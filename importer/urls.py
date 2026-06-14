from django.urls import path
from .views import (
    ImportCSVView,
    ImportReportView,
    ApproveAnomalyView
)

urlpatterns = [
    path('upload/', ImportCSVView.as_view(), name='import-csv'),
    path('report/<int:batch_id>/', ImportReportView.as_view(), name='import-report'),
    path('anomalies/<int:anomaly_id>/approve/', ApproveAnomalyView.as_view(), name='approve-anomaly'),
]
