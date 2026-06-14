from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, F, Case, When, DecimalField, Value
from django.utils import timezone
from decimal import Decimal
from groups.models import Group, GroupMember
from .models import Expense, ExpenseSplit, Settlement
from .serializers import ExpenseSerializer, ExpenseSplitSerializer, SettlementSerializer

User = __import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model()


class ExpenseListCreateView(generics.ListCreateAPIView):
    """
    List and create expenses for a group.
    """
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(Group, id=group_id)
        
        # Verify user is a member of this group
        if not GroupMember.objects.filter(group=group, user=self.request.user, left_at__isnull=True).exists():
            return Expense.objects.none()
        
        return Expense.objects.filter(group=group, is_deleted=False)
    
    def perform_create(self, serializer):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(Group, id=group_id)
        
        # Verify user is a member of this group
        if not GroupMember.objects.filter(group=group, user=self.request.user, left_at__isnull=True).exists():
            raise PermissionError('You are not a member of this group')
        
        serializer.save(group=group, paid_by=self.request.user)


class ExpenseDetailView(generics.RetrieveAPIView):
    """
    Get a single expense with full split breakdown.
    """
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only allow viewing expenses from groups user is a member of"""
        user = self.request.user
        group_ids = GroupMember.objects.filter(
            user=user,
            left_at__isnull=True
        ).values_list('group_id', flat=True)
        return Expense.objects.filter(group_id__in=group_ids, is_deleted=False)


class BalanceView(generics.GenericAPIView):
    """
    Calculate who owes whom in a group using a greedy algorithm.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(Group, id=group_id)
        
        # Verify user is a member of this group
        if not GroupMember.objects.filter(group=group, user=request.user, left_at__isnull=True).exists():
            return Response(
                {'detail': 'You are not a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all active members of the group
        members = GroupMember.objects.filter(
            group=group,
            left_at__isnull=True
        ).values_list('user_id', flat=True)
        
        # Calculate net balance for each member
        balances = {}
        for member_id in members:
            # Total paid by this user
            total_paid = Expense.objects.filter(
                group=group,
                paid_by_id=member_id,
                is_deleted=False
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Total owed by this user
            total_owed = ExpenseSplit.objects.filter(
                user_id=member_id,
                expense__group=group,
                expense__is_deleted=False
            ).aggregate(total=Sum('owed_amount'))['total'] or Decimal('0')
            
            net = total_paid - total_owed
            balances[member_id] = net
        
        # Use greedy algorithm to minimize transactions
        transactions = self._minimize_transactions(balances)
        
        # Convert user IDs to user details
        result = []
        for from_user_id, to_user_id, amount in transactions:
            from_user = User.objects.get(id=from_user_id)
            to_user = User.objects.get(id=to_user_id)
            result.append({
                'from_user': {'id': from_user.id, 'email': from_user.email, 'name': from_user.name},
                'to_user': {'id': to_user.id, 'email': to_user.email, 'name': to_user.name},
                'amount': str(amount)
            })
        
        return Response({
            'group_id': group_id,
            'balances': {k: str(v) for k, v in balances.items()},
            'transactions': result
        })
    
    def _minimize_transactions(self, balances):
        """
        Greedy algorithm to minimize transactions.
        Returns list of tuples: (from_user_id, to_user_id, amount)
        """
        transactions = []
        
        # Separate debtors and creditors
        debtors = []  # (user_id, amount_owed)
        creditors = []  # (user_id, amount_owed)
        
        for user_id, balance in balances.items():
            if balance < 0:
                debtors.append([user_id, abs(balance)])
            elif balance > 0:
                creditors.append([user_id, balance])
        
        # Match debtors with creditors
        while debtors and creditors:
            debtor_id, debt_amount = debtors[0]
            creditor_id, credit_amount = creditors[0]
            
            # Settle as much as possible
            settle_amount = min(debt_amount, credit_amount)
            transactions.append((debtor_id, creditor_id, settle_amount))
            
            # Update amounts
            debtors[0][1] -= settle_amount
            creditors[0][1] -= settle_amount
            
            # Remove if settled
            if debtors[0][1] == 0:
                debtors.pop(0)
            if creditors[0][1] == 0:
                creditors.pop(0)
        
        return transactions


class SettlementCreateView(generics.CreateAPIView):
    """
    Record a payment between two members.
    """
    serializer_class = SettlementSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save()

