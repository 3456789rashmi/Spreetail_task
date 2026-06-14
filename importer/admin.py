from django.contrib import admin
from .models import ImportBatch, ImportAnomaly


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ['filename', 'status', 'imported_by', 'imported_at']
    list_filter = ['status', 'imported_at']
    search_fields = ['filename', 'imported_by__email']
    readonly_fields = ['id', 'imported_at']
    fieldsets = (
        ('Batch Info', {'fields': ('id', 'filename', 'imported_by')}),
        ('Status', {'fields': ('status',)}),
        ('Meta', {'fields': ('imported_at',)}),
    )


@admin.register(ImportAnomaly)
class ImportAnomalyAdmin(admin.ModelAdmin):
    list_display = ['batch', 'row_number', 'anomaly_type', 'requires_approval', 'is_approved']
    list_filter = ['batch', 'anomaly_type', 'requires_approval', 'is_approved']
    search_fields = ['batch__filename', 'description', 'anomaly_type']
    readonly_fields = ['id', 'batch', 'row_number', 'anomaly_type']
    fieldsets = (
        ('Anomaly Info', {'fields': ('id', 'batch', 'row_number', 'anomaly_type')}),
        ('Details', {'fields': ('description', 'action_taken')}),
        ('Approval', {'fields': ('requires_approval', 'is_approved', 'approved_by', 'approved_at')}),
    )
