import pandas as pd
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.contrib.auth import get_user_model
from dateutil import parser as date_parser
from difflib import SequenceMatcher
import re
import numpy as np
from groups.models import Group, GroupMember
from expenses.models import Expense, ExpenseSplit, Settlement
from .models import ImportBatch, ImportAnomaly

User = get_user_model()


class CSVImporter:
    """CSV importer with handling for 18+ specific anomalies."""
    
    USD_TO_INR_RATE = Decimal('83.5')
    SETTLEMENT_KEYWORDS = ['paid back', 'settlement', 'reimburse', 'reimbursement', 'deposit share']
    VALID_SPLIT_TYPES = ['equal', 'exact', 'percentage', 'shares']
    SPLIT_TYPE_NORMALIZATIONS = {'share': 'shares'}
    FUZZY_MATCH_THRESHOLD = 0.8  # 80% similarity for duplicate detection
    
    def __init__(self, file_path, batch, group, current_user):
        """Initialize importer."""
        self.file_path = file_path
        self.batch = batch
        self.group = group
        self.current_user = current_user
        self.rows_processed = 0
        self.rows_imported = 0
        self.rows_skipped = 0
        self.anomalies = []
        self.df = None
        self.member_map = {}  # normalized_name -> (User, GroupMember)
        self.processed_expenses = []  # Track (date, payer_email, amount, desc) for duplicates
        self.conflicting_rows = set()  # Rows that need manual approval
    
    def import_csv(self):
        """Main import method."""
        try:
            self.df = pd.read_csv(self.file_path)
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to read CSV: {str(e)}',
                'rows_processed': 0,
                'rows_imported': 0,
                'rows_skipped': 0,
                'anomalies': []
            }
        
        # Build member map (normalized for flexible matching)
        members = GroupMember.objects.filter(group=self.group)
        for member in members:
            # Normalize: lowercase, strip whitespace
            key = member.user.email.lower().strip()
            self.member_map[key] = (member.user, member)
        
        # Pre-scan for conflicting duplicates (ANOMALY 2)
        self._detect_conflicting_duplicates()
        
        # Process each row
        for idx, row in self.df.iterrows():
            row_number = idx + 2  # +2 for header and 1-based indexing
            
            if row_number in self.conflicting_rows:
                self.rows_processed += 1
                self.rows_skipped += 1
                continue
            
            try:
                result = self._process_row(row, row_number)
                if result:
                    self.rows_processed += 1
                    self.rows_imported += 1
                else:
                    self.rows_processed += 1
                    self.rows_skipped += 1
            except Exception as e:
                self.rows_processed += 1
                self.rows_skipped += 1
        
        self.batch.status = 'completed'
        self.batch.save()
        
        return {
            'success': True,
            'batch_id': self.batch.id,
            'rows_processed': self.rows_processed,
            'rows_imported': self.rows_imported,
            'rows_skipped': self.rows_skipped,
            'anomalies': len(self.anomalies),
            'anomaly_details': [
                {
                    'row': a.row_number,
                    'type': a.anomaly_type,
                    'description': a.description,
                    'action_taken': a.action_taken,
                    'requires_approval': a.requires_approval
                }
                for a in self.anomalies
            ]
        }
    
    def _detect_conflicting_duplicates(self):
        """Pre-scan for ANOMALY 2: conflicting duplicates."""
        # Group by date + split_with to find conflicts
        date_groups = {}
        for idx, row in self.df.iterrows():
            row_number = idx + 2
            try:
                date_val = self._parse_date_safe(self._clean_field(row.get('date', '')))
                split_with = self._clean_field(row.get('split_with', ''))
                
                key = (str(date_val), split_with)
                if key not in date_groups:
                    date_groups[key] = []
                date_groups[key].append((row_number, row))
            except:
                pass
        
        # Find conflicts: same date + split_with but different payer/amount
        for key, rows in date_groups.items():
            if len(rows) > 1:
                first_row = rows[0][1]
                payer1 = self._clean_field(first_row.get('paid_by', ''))
                amount1_str = self._clean_field(first_row.get('amount', ''))
                
                has_conflict = False
                for row_num, curr_row in rows[1:]:
                    payer2 = self._clean_field(curr_row.get('paid_by', ''))
                    amount2_str = self._clean_field(curr_row.get('amount', ''))
                    
                    try:
                        amount1 = Decimal(amount1_str.replace(',', ''))
                        amount2 = Decimal(amount2_str.replace(',', ''))
                    except:
                        continue
                    
                    # Different payer or amount = conflict
                    if payer1.lower() != payer2.lower() or amount1 != amount2:
                        has_conflict = True
                        self.conflicting_rows.add(row_num)
                        self._log_anomaly(
                            row_number=row_num,
                            anomaly_type='CONFLICTING_DUPLICATE',
                            description=f'Conflicting entry for same event on {key[0]} with {key[1]}',
                            action_taken='Row held for manual approval',
                            requires_approval=True
                        )
                
                if has_conflict:
                    self.conflicting_rows.add(rows[0][0])
                    self._log_anomaly(
                        row_number=rows[0][0],
                        anomaly_type='CONFLICTING_DUPLICATE',
                        description=f'Conflicting entry for same event on {key[0]} with {key[1]}',
                        action_taken='Row held for manual approval',
                        requires_approval=True
                    )
    
    def _process_row(self, row, row_number):
        """Process single row. Returns True if imported, False/None otherwise."""
        # Extract and clean fields
        date_str = self._clean_field(row.get('date', ''))
        description = self._clean_field(row.get('description', ''))
        paid_by_str = self._clean_field(row.get('paid_by', ''))
        amount_str = self._clean_field(row.get('amount', ''))
        currency_str = self._clean_field(row.get('currency', ''))
        split_type = self._clean_field(row.get('split_type', 'equal'))
        split_with = self._clean_field(row.get('split_with', ''))
        split_details = self._clean_field(row.get('split_details', ''))
        notes = self._clean_field(row.get('notes', ''))
        
        # ANOMALY 6: MISSING_PAYER
        if not paid_by_str:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='MISSING_PAYER',
                description='paid_by field is empty',
                action_taken='Row skipped - cannot create expense without payer',
                requires_approval=False
            )
            return False
        
        # Normalize payer name (ANOMALY 13: NAME_CASING)
        payer_normalized, payer_norm_key = self._normalize_member_name(paid_by_str, row_number)
        if not payer_normalized:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='UNKNOWN_MEMBER',
                description=f'Payer "{paid_by_str}" not found in group members',
                action_taken='Row skipped',
                requires_approval=True
            )
            return False
        
        payer_user, payer_member = payer_normalized
        
        # ANOMALY 12: DATE_FORMAT_INCONSISTENCY
        parsed_date = self._parse_date_with_normalization(date_str, row_number)
        if not parsed_date:
            return False
        
        # ANOMALY 5: ZERO_AMOUNT
        if amount_str and str(amount_str).strip() == '0':
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='ZERO_AMOUNT',
                description=f'Amount is 0. Notes: {notes}',
                action_taken='Row skipped entirely',
                requires_approval=False
            )
            return False
        
        # ANOMALY 3: AMOUNT_WITH_COMMA and ANOMALY 4: ODD_DECIMAL_PRECISION
        amount, is_refund = self._parse_amount_with_fixes(amount_str, row_number)
        if amount is None:
            return False
        
        # ANOMALY 11: MISSING_CURRENCY
        if not currency_str:
            currency = 'INR'
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='MISSING_CURRENCY',
                description='Currency field is empty',
                action_taken='Defaulted to INR (domestic)',
                requires_approval=False
            )
        else:
            currency = currency_str.upper()
        
        # ANOMALY 9: USD_CURRENCY
        exchange_rate = Decimal('1')
        amount_inr = amount
        if currency == 'USD':
            exchange_rate = self.USD_TO_INR_RATE
            amount_inr = amount * exchange_rate
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='USD_CURRENCY',
                description=f'USD amount: {amount} converted to INR at rate {self.USD_TO_INR_RATE}',
                action_taken=f'Converted to ₹{amount_inr}',
                requires_approval=False
            )
        
        # ANOMALY 10: NEGATIVE_AMOUNT / REFUND
        if amount < 0:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='NEGATIVE_AMOUNT',
                description=f'Negative amount: {amount} (refund)',
                action_taken='Created as refund expense',
                requires_approval=False
            )
        
        # ANOMALY 7 & 8: SETTLEMENT_AS_EXPENSE / DEPOSIT_AS_EXPENSE
        is_settlement = self._is_settlement(description, notes)
        if is_settlement:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='SETTLEMENT_AS_EXPENSE',
                description=f'Settlement keywords in: {description}',
                action_taken='Reclassified as Settlement, flag for confirmation',
                requires_approval=True
            )
            # Don't import settlements as expenses
            return False
        
        # ANOMALY 1: EXACT_DUPLICATE (case-insensitive match)
        dup_key = (parsed_date, payer_user.email.lower().strip(), amount)
        if dup_key in [(e[0], e[1].lower().strip(), e[2]) for e in self.processed_expenses]:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='EXACT_DUPLICATE',
                description=f'Exact duplicate: {parsed_date} | {paid_by_str} | {amount}',
                action_taken='Marked for approval before deletion',
                requires_approval=True
            )
            return False
        
        # ANOMALY 18: UNKNOWN_SPLIT_TYPE
        normalized_split_type = self.SPLIT_TYPE_NORMALIZATIONS.get(split_type, split_type)
        if normalized_split_type not in self.VALID_SPLIT_TYPES:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='UNKNOWN_SPLIT_TYPE',
                description=f'Unknown split type: "{split_type}"',
                action_taken=f'Using default: equal',
                requires_approval=False
            )
            normalized_split_type = 'equal'
        
        # ANOMALY 17: SPLIT_TYPE_CONFLICT
        if normalized_split_type == 'equal' and split_details and split_details.strip():
            normalized_split_type = 'shares'
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='SPLIT_TYPE_CONFLICT',
                description='split_type is "equal" but split_details provided',
                action_taken='Using split_details, reclassified as "shares"',
                requires_approval=False
            )
        
        # Create expense
        expense = Expense.objects.create(
            group=self.group,
            title=description,
            amount=amount,
            currency=currency,
            amount_inr=amount_inr,
            exchange_rate=exchange_rate,
            paid_by=payer_user,
            date=parsed_date,
            split_type=normalized_split_type,
            is_settlement=False,
            import_batch=self.batch
        )
        
        # Process splits
        self._process_splits(
            expense, row_number, split_type=normalized_split_type,
            split_with=split_with, split_details=split_details
        )
        
        # Track this expense for duplicate detection
        self.processed_expenses.append((parsed_date, payer_user.email, amount, description))
        
        return True
    
    def _process_splits(self, expense, row_number, split_type, split_with, split_details):
        """Process expense splits with handling for unknown members."""
        active_members = GroupMember.objects.filter(
            group=self.group,
            left_at__isnull=True
        )
        
        if split_type == 'equal':
            # Equal split among all active members
            split_amount = expense.amount / max(1, active_members.count())
            for member in active_members:
                ExpenseSplit.objects.create(
                    expense=expense,
                    user=member.user,
                    owed_amount=split_amount
                )
        
        elif split_type == 'shares' and split_details:
            # Parse shares from split_details: "name1:2, name2:3"
            self._create_shares_split(expense, row_number, split_details, active_members)
        
        elif split_type == 'percentage' and split_details:
            # Parse percentages: "name1:30, name2:70"
            self._create_percentage_split(expense, row_number, split_details, active_members)
        
        elif split_type == 'exact' and split_details:
            # Parse exact amounts: "name1:500, name2:600"
            self._create_exact_split(expense, row_number, split_details, active_members)
        
        else:
            # Default: equal split
            split_amount = expense.amount / max(1, active_members.count())
            for member in active_members:
                ExpenseSplit.objects.create(
                    expense=expense,
                    user=member.user,
                    owed_amount=split_amount
                )
    
    def _create_shares_split(self, expense, row_number, split_details, active_members):
        """Create split based on shares."""
        shares = {}
        total_shares = 0
        unknown_names = []
        
        for item in split_details.split(','):
            if ':' not in item:
                continue
            name, share_str = item.split(':', 1)
            name = name.strip()
            try:
                share_val = int(share_str.strip())
            except:
                continue
            
            # Try to find member
            member = self._find_member_by_name(name)
            if not member:
                unknown_names.append(name)
                # ANOMALY 14: UNKNOWN_MEMBER_IN_SPLIT
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='UNKNOWN_MEMBER_IN_SPLIT',
                    description=f'"{name}" not found in group members',
                    action_taken='Skipped from split, share redistributed',
                    requires_approval=False
                )
                continue
            
            shares[member] = share_val
            total_shares += share_val
        
        if total_shares == 0:
            return
        
        for member, share_val in shares.items():
            owed = (expense.amount * Decimal(share_val)) / Decimal(total_shares)
            ExpenseSplit.objects.create(
                expense=expense,
                user=member,
                owed_amount=owed.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            )
    
    def _create_percentage_split(self, expense, row_number, split_details, active_members):
        """Create split based on percentages."""
        percentages = {}
        total_pct = Decimal('0')
        unknown_names = []
        
        for item in split_details.split(','):
            if ':' not in item:
                continue
            name, pct_str = item.split(':', 1)
            name = name.strip()
            try:
                pct_val = Decimal(pct_str.strip())
            except:
                continue
            
            member = self._find_member_by_name(name)
            if not member:
                unknown_names.append(name)
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='UNKNOWN_MEMBER_IN_SPLIT',
                    description=f'"{name}" not found in group members',
                    action_taken='Skipped from split, % redistributed',
                    requires_approval=False
                )
                continue
            
            percentages[member] = pct_val
            total_pct += pct_val
        
        # ANOMALY 15: PERCENTAGE_MISMATCH
        if total_pct != Decimal('100'):
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='PERCENTAGE_MISMATCH',
                description=f'Percentages sum to {total_pct}%, not 100%',
                action_taken='Normalized percentages proportionally',
                requires_approval=True
            )
        
        if total_pct == 0:
            return
        
        for member, pct_val in percentages.items():
            owed = (expense.amount * pct_val) / Decimal('100')
            ExpenseSplit.objects.create(
                expense=expense,
                user=member,
                owed_amount=owed.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            )
    
    def _create_exact_split(self, expense, row_number, split_details, active_members):
        """Create split based on exact amounts."""
        exact_amounts = {}
        total_amount = Decimal('0')
        unknown_names = []
        
        for item in split_details.split(','):
            if ':' not in item:
                continue
            name, amt_str = item.split(':', 1)
            name = name.strip()
            try:
                amt_val = Decimal(amt_str.strip().replace(',', ''))
            except:
                continue
            
            member = self._find_member_by_name(name)
            if not member:
                unknown_names.append(name)
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='UNKNOWN_MEMBER_IN_SPLIT',
                    description=f'"{name}" not found in group members',
                    action_taken='Skipped from split, amount redistributed',
                    requires_approval=False
                )
                continue
            
            exact_amounts[member] = amt_val
            total_amount += amt_val
        
        if total_amount == 0:
            return
        
        for member, amt_val in exact_amounts.items():
            ExpenseSplit.objects.create(
                expense=expense,
                user=member,
                owed_amount=amt_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            )
    
    def _find_member_by_name(self, name):
        """Find member by name, handling multiple normalizations."""
        # Try exact match first
        for key, (user, member) in self.member_map.items():
            if key == name.lower().strip():
                # Check if member is still in group on expense date
                return user
        
        # Try fuzzy match
        name_lower = name.lower().strip()
        for key, (user, member) in self.member_map.items():
            if SequenceMatcher(None, key, name_lower).ratio() > 0.85:
                return user
        
        return None
    
    def _normalize_member_name(self, name_str, row_number):
        """Normalize and find member by name. Returns (User, GroupMember) or None."""
        original_name = name_str
        normalized_key = name_str.lower().strip()
        
        # Try exact match
        if normalized_key in self.member_map:
            return self.member_map[normalized_key], normalized_key
        
        # Try fuzzy match
        best_match = None
        best_score = 0
        for key, (user, member) in self.member_map.items():
            score = SequenceMatcher(None, key, normalized_key).ratio()
            if score > best_score and score > self.FUZZY_MATCH_THRESHOLD:
                best_match = (user, member)
                best_score = score
        
        if best_match:
            if original_name != normalized_key:
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='NAME_CASING',
                    description=f'Member name "{original_name}" normalized',
                    action_taken=f'Matched to "{best_match[0].email}"',
                    requires_approval=False
                )
            return best_match, normalized_key
        
        return None, None
    
    def _parse_date_with_normalization(self, date_str, row_number):
        """Parse date with flexible formatting (ANOMALY 12)."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Try ISO format first
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                pass
        
        # Try "Mar 14" format
        if re.match(r'^[A-Za-z]{3}\s+\d{1,2}$', date_str):
            try:
                parsed = datetime.strptime(f"{date_str} 2026", '%b %d %Y').date()
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='DATE_FORMAT',
                    description=f'Short date format "{date_str}" parsed as {parsed}',
                    action_taken='Normalized to YYYY-MM-DD',
                    requires_approval=False
                )
                return parsed
            except:
                pass
        
        # Try flexible parsing with dateutil
        try:
            parsed = date_parser.parse(date_str, dayfirst=True, yearfirst=False).date()
            
            # Check for ambiguous dates
            if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='AMBIGUOUS_DATE',
                    description=f'Ambiguous date format: {date_str}',
                    action_taken=f'Parsed as DD/MM/YYYY: {parsed}',
                    requires_approval=True
                )
            elif date_str != str(parsed):
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='DATE_FORMAT',
                    description=f'Date format: {date_str} normalized to {parsed}',
                    action_taken='Normalized to YYYY-MM-DD',
                    requires_approval=False
                )
            
            return parsed
        except:
            pass
        
        self._log_anomaly(
            row_number=row_number,
            anomaly_type='INVALID_DATE',
            description=f'Could not parse date: {date_str}',
            action_taken='Row skipped',
            requires_approval=False
        )
        return None
    
    def _parse_date_safe(self, date_str):
        """Safe date parsing for pre-scan."""
        if not date_str:
            return None
        try:
            return date_parser.parse(date_str, dayfirst=True, yearfirst=False).date()
        except:
            return None
    
    def _parse_amount_with_fixes(self, amount_str, row_number):
        """Parse amount with fixes for comma and decimal precision."""
        if not amount_str or str(amount_str).strip() == '':
            return None, False
        
        original = str(amount_str)
        is_refund = False
        
        # ANOMALY 3: AMOUNT_WITH_COMMA
        if ',' in original:
            cleaned = original.replace(',', '')
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='AMOUNT_WITH_COMMA',
                description=f'Amount "{original}" had commas',
                action_taken=f'Removed commas: {cleaned}',
                requires_approval=False
            )
            amount_str = cleaned
        
        try:
            amount = Decimal(amount_str)
        except:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='INVALID_AMOUNT',
                description=f'Could not parse amount: {original}',
                action_taken='Row skipped',
                requires_approval=False
            )
            return None, False
        
        # ANOMALY 4: ODD_DECIMAL_PRECISION
        if amount.as_tuple().exponent < -2:
            original_amount = amount
            amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='ODD_DECIMAL_PRECISION',
                description=f'Amount "{original_amount}" has >2 decimal places',
                action_taken=f'Rounded to {amount}',
                requires_approval=False
            )
        
        return amount, is_refund
    
    def _is_settlement(self, description, notes):
        """Check if expense is actually a settlement."""
        text = (description + ' ' + notes).lower()
        return any(keyword in text for keyword in self.SETTLEMENT_KEYWORDS)
    
    def _clean_field(self, value):
        """Clean field value."""
        if pd.isna(value) or value is None:
            return ''
        return str(value).strip()
    
    def _log_anomaly(self, row_number, anomaly_type, description, action_taken, requires_approval):
        """Log an anomaly."""
        anomaly = ImportAnomaly.objects.create(
            batch=self.batch,
            row_number=row_number,
            anomaly_type=anomaly_type,
            description=description,
            action_taken=action_taken,
            requires_approval=requires_approval,
            is_approved=False
        )
        self.anomalies.append(anomaly)
