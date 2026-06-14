from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Expense, ExpenseSplit, Settlement

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name']


class ExpenseSplitSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = ExpenseSplit
        fields = ['id', 'user', 'owed_amount', 'is_settled']


class ExpenseSerializer(serializers.ModelSerializer):
    splits = ExpenseSplitSerializer(many=True, read_only=True)
    paid_by = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id',
            'group',
            'title',
            'amount',
            'currency',
            'amount_inr',
            'exchange_rate',
            'paid_by',
            'date',
            'split_type',
            'is_settlement',
            'is_deleted',
            'splits',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'amount_inr']


class SettlementSerializer(serializers.ModelSerializer):
    from_user = UserSimpleSerializer(read_only=True)
    to_user = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = Settlement
        fields = ['id', 'group', 'from_user', 'to_user', 'amount', 'date', 'created_at']
        read_only_fields = ['id', 'created_at']
