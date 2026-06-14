import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from groups.models import Group, GroupMember
from expenses.models import Expense, ExpenseSplit, Settlement
from .models import ImportBatch, ImportAnomaly

User = get_user_model()


class CSVImporter:
    """CSV importer that detects anomalies and creates expense records."""
    
    ANOMALY_TYPES = {
        'DUPLICATE': 'Duplicate expense detected',
        'NEGATIVE_AMOUNT': 'Negative amount (refund)',
        'USD_CURRENCY': 'USD currency converted to INR',
        'SETTLEMENT_AS_EXPENSE': 'Settlement marked as expense',
        'MISSING_FIELD': 'Missing required field',
        'UNKNOWN_MEMBER': 'User not found in group',
        'MEMBER_LEFT': 'Member had left group at this date',
        'MEMBER_NOT_YET_JOINED': 'Member had not joined at this date',
        'DATE_FORMAT': 'Non-standard date format normalized',
        'AMOUNT_FORMAT': 'Amount format cleaned (₹ or commas removed)',
        'SPLIT_MISMATCH': 'Split amounts do not match total',
        'FUTURE_DATE': 'Expense date is in the future'
    }
    
    USD_TO_INR_RATE = Decimal('83.5')
    
    def __init__(self, file_obj, batch, group, current_user):
        """Initialize importer with file and context."""
        self.file_obj = file_obj
        self.batch = batch
        self.group = group
        self.current_user = current_user
        self.rows_processed = 0
        self.rows_imported = 0
        self.rows_skipped = 0
        self.anomalies = []
        self.df = None
    
    def import_csv(self):
        """Main import method. Returns summary report."""
        try:
            self.df = pd.read_csv(self.file_obj)
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to read CSV: {str(e)}',
                'rows_processed': 0,
                'rows_imported': 0,
                'rows_skipped': 0,
                'anomalies': []
            }
        
        # Get all group members
        members = GroupMember.objects.filter(group=self.group)
        member_emails = {m.user.email.lower(): m for m in members}
        
        for idx, row in self.df.iterrows():
            self.rows_processed += 1
            row_number = idx + 2  # +2 for header and 0-indexing
            
            try:
                self._process_row(row, row_number, member_emails)
                self.rows_imported += 1
            except Exception as e:
                self.rows_skipped += 1
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='MISSING_FIELD',
                    description=str(e),
                    action_taken='Row skipped',
                    requires_approval=False
                )
        
        # Update batch status
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
                    'requires_approval': a.requires_approval
                }
                for a in self.anomalies
            ]
        }
    
    def _process_row(self, row, row_number, member_emails):
        """Process a single row."""
        # Extract fields
        date_str = self._clean_field(row.get('date', ''))
        amount_str = self._clean_field(row.get('amount', ''))
        payer_email = self._clean_field(row.get('payer_email', ''))
        description = self._clean_field(row.get('description', ''))
        currency = self._clean_field(row.get('currency', 'INR')).upper()
        split_data = row.get('split_data', '')  # JSON or comma-separated
        
        # Check missing fields
        if not date_str or not amount_str or not payer_email:
            raise ValueError('Missing required field: date, amount, or payer_email')
        
        # Normalize and validate date
        parsed_date = self._parse_date(date_str, row_number)
        
        # Check for future date
        if parsed_date > date.today():
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='FUTURE_DATE',
                description=f'Expense date {parsed_date} is in the future',
                action_taken='Logged for review',
                requires_approval=True
            )
        
        # Parse and validate amount
        amount = self._parse_amount(amount_str, row_number)
        
        # Check for negative amount (refund)
        if amount < 0:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='NEGATIVE_AMOUNT',
                description=f'Negative amount detected: {amount}',
                action_taken='Treated as refund/settlement',
                requires_approval=True
            )
        
        # Check for settlement keywords
        is_settlement = self._detect_settlement(description)
        if is_settlement:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='SETTLEMENT_AS_EXPENSE',
                description=f'Settlement keywords detected in: {description}',
                action_taken='Classified as settlement',
                requires_approval=False
            )
        
        # Handle currency conversion
        exchange_rate = Decimal('1.0')
        amount_inr = amount
        if currency != 'INR':
            if currency == 'USD':
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='USD_CURRENCY',
                    description=f'USD amount converted using rate {self.USD_TO_INR_RATE}',
                    action_taken=f'Converted {amount} USD to INR',
                    requires_approval=False
                )
                exchange_rate = self.USD_TO_INR_RATE
                amount_inr = amount * exchange_rate
        
        # Find payer user
        payer = self._get_user_by_email(payer_email)
        if not payer:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='UNKNOWN_MEMBER',
                description=f'Payer email {payer_email} not found',
                action_taken='Row skipped',
                requires_approval=True
            )
            raise ValueError(f'Payer {payer_email} not found')
        
        # Check for duplicate
        if self._check_duplicate(payer, amount, description, parsed_date):
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='DUPLICATE',
                description=f'Duplicate: {parsed_date} | {payer_email} | {amount}',
                action_taken='Duplicate skipped',
                requires_approval=False
            )
            raise ValueError('Duplicate expense detected')
        
        # Create expense
        expense = Expense.objects.create(
            group=self.group,
            title=description,
            amount=amount,
            currency=currency,
            amount_inr=amount_inr,
            exchange_rate=exchange_rate,
            paid_by=payer,
            date=parsed_date,
            split_type='equal',
            is_settlement=is_settlement,
            import_batch=self.batch
        )
        
        # Process splits
        self._process_splits(expense, split_data, member_emails, row_number)
    
    def _process_splits(self, expense, split_data, member_emails, row_number):
        """Process expense splits."""
        if not split_data or pd.isna(split_data):
            # Default: split equally among all active members
            active_members = [m for m in member_emails.values() if m.left_at is None]
            if not active_members:
                return
            
            split_amount = expense.amount / len(active_members)
            for member in active_members:
                ExpenseSplit.objects.create(
                    expense=expense,
                    user=member.user,
                    owed_amount=split_amount
                )
        else:
            # Parse split data
            try:
                splits = self._parse_split_data(split_data)
            except ValueError as e:
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='SPLIT_MISMATCH',
                    description=str(e),
                    action_taken='Used equal split',
                    requires_approval=True
                )
                # Fallback to equal split
                active_members = [m for m in member_emails.values() if m.left_at is None]
                split_amount = expense.amount / len(active_members)
                for member in active_members:
                    ExpenseSplit.objects.create(
                        expense=expense,
                        user=member.user,
                        owed_amount=split_amount
                    )
                return
            
            total_split = Decimal('0')
            split_records = []
            
            for email, amount in splits.items():
                email_lower = email.lower()
                if email_lower not in member_emails:
                    self._log_anomaly(
                        row_number=row_number,
                        anomaly_type='UNKNOWN_MEMBER',
                        description=f'Split user {email} not in group',
                        action_taken='Excluded from split',
                        requires_approval=False
                    )
                    continue
                
                member = member_emails[email_lower]
                
                # Check member timeline
                if member.left_at and expense.date >= member.left_at.date():
                    self._log_anomaly(
                        row_number=row_number,
                        anomaly_type='MEMBER_LEFT',
                        description=f'{email} had left group by {expense.date}',
                        action_taken='Excluded from split',
                        requires_approval=False
                    )
                    continue
                
                if expense.date < member.joined_at.date():
                    self._log_anomaly(
                        row_number=row_number,
                        anomaly_type='MEMBER_NOT_YET_JOINED',
                        description=f'{email} had not joined by {expense.date}',
                        action_taken='Excluded from split',
                        requires_approval=False
                    )
                    continue
                
                split_records.append((member.user, amount))
                total_split += amount
            
            # Verify total matches
            if total_split != expense.amount:
                self._log_anomaly(
                    row_number=row_number,
                    anomaly_type='SPLIT_MISMATCH',
                    description=f'Split total {total_split} != expense {expense.amount}',
                    action_taken='Adjusted to match expense total',
                    requires_approval=True
                )
            
            # Create split records
            for user, amount in split_records:
                ExpenseSplit.objects.create(
                    expense=expense,
                    user=user,
                    owed_amount=amount
                )
    
    def _parse_date(self, date_str, row_number):
        """Parse and normalize date."""
        date_formats = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%m-%d-%Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y/%m/%d',
            '%d.%m.%Y',
            '%Y.%m.%d',
        ]
        
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_str, fmt).date()
                if fmt != '%Y-%m-%d':
                    self._log_anomaly(
                        row_number=row_number,
                        anomaly_type='DATE_FORMAT',
                        description=f'Date format: {date_str} normalized to {parsed}',
                        action_taken='Normalized to YYYY-MM-DD',
                        requires_approval=False
                    )
                return parsed
            except ValueError:
                continue
        
        raise ValueError(f'Invalid date format: {date_str}')
    
    def _parse_amount(self, amount_str, row_number):
        """Parse and clean amount."""
        original = amount_str
        # Remove currency symbols and commas
        amount_str = amount_str.replace('₹', '').replace('$', '').replace(',', '').strip()
        
        if original != amount_str:
            self._log_anomaly(
                row_number=row_number,
                anomaly_type='AMOUNT_FORMAT',
                description=f'Amount format cleaned: {original} → {amount_str}',
                action_taken='Symbols and commas removed',
                requires_approval=False
            )
        
        try:
            return Decimal(amount_str)
        except:
            raise ValueError(f'Invalid amount: {amount_str}')
    
    def _parse_split_data(self, split_data):
        """Parse split data (expects format: email1:amount1,email2:amount2)."""
        if pd.isna(split_data):
            return {}
        
        splits = {}
        for item in str(split_data).split(','):
            if ':' not in item:
                raise ValueError(f'Invalid split format: {split_data}')
            email, amount = item.split(':')
            splits[email.strip()] = Decimal(amount.strip())
        
        return splits
    
    def _detect_settlement(self, description):
        """Detect settlement keywords in description."""
        keywords = ['settlement', 'paid back', 'reimburse', 'reimbursement', 'refund']
        desc_lower = description.lower()
        return any(keyword in desc_lower for keyword in keywords)
    
    def _check_duplicate(self, user, amount, description, date_obj):
        """Check if expense already exists."""
        return Expense.objects.filter(
            group=self.group,
            paid_by=user,
            amount=amount,
            title=description,
            date=date_obj,
            is_deleted=False
        ).exists()
    
    def _get_user_by_email(self, email):
        """Get user by email."""
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None
    
    def _clean_field(self, value):
        """Clean field value."""
        if pd.isna(value):
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
