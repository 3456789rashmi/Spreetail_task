from django.urls import path
from .views import (
    ExpenseListCreateView,
    ExpenseDetailView,
    BalanceView,
    SettlementCreateView
)

urlpatterns = [
    path('group/<int:group_id>/', ExpenseListCreateView.as_view(), name='expense-list-create'),
    path('detail/<int:pk>/', ExpenseDetailView.as_view(), name='expense-detail'),
    path('group/<int:group_id>/balances/', BalanceView.as_view(), name='balance-view'),
    path('settlements/', SettlementCreateView.as_view(), name='settlement-create'),
]
