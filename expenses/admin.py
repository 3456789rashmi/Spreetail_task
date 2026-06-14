from django.contrib import admin
from .models import Expense, ExpenseSplit, Settlement


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'group', 'paid_by', 'amount', 'currency', 'date', 'is_settlement', 'is_deleted']
    list_filter = ['group', 'currency', 'split_type', 'is_settlement', 'is_deleted', 'date', 'created_at']
    search_fields = ['title', 'paid_by__email', 'group__name']
    readonly_fields = ['id', 'created_at', 'amount_inr']
    fieldsets = (
        ('Expense Info', {'fields': ('id', 'group', 'title', 'paid_by')}),
        ('Amount', {'fields': ('amount', 'currency', 'exchange_rate', 'amount_inr')}),
        ('Split', {'fields': ('split_type', 'date')}),
        ('Flags', {'fields': ('is_settlement', 'is_deleted', 'import_batch')}),
        ('Meta', {'fields': ('created_at',)}),
    )


@admin.register(ExpenseSplit)
class ExpenseSplitAdmin(admin.ModelAdmin):
    list_display = ['user', 'expense', 'owed_amount', 'is_settled']
    list_filter = ['expense__group', 'is_settled']
    search_fields = ['user__email', 'expense__title']
    readonly_fields = ['id']
    fieldsets = (
        ('Split Info', {'fields': ('id', 'expense', 'user')}),
        ('Amount', {'fields': ('owed_amount',)}),
        ('Status', {'fields': ('is_settled',)}),
    )


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'group', 'amount', 'date', 'created_at']
    list_filter = ['group', 'date', 'created_at']
    search_fields = ['from_user__email', 'to_user__email', 'group__name']
    readonly_fields = ['id', 'created_at']
    fieldsets = (
        ('Settlement Info', {'fields': ('id', 'group', 'from_user', 'to_user')}),
        ('Amount', {'fields': ('amount',)}),
        ('Timeline', {'fields': ('date', 'created_at')}),
    )
