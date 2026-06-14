from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ImportBatch(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.AutoField(primary_key=True)
    filename = models.CharField(max_length=255)
    imported_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    imported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='import_batches')
    
    class Meta:
        ordering = ['-imported_at']
    
    def __str__(self):
        return f"{self.filename} ({self.status})"


class ImportAnomaly(models.Model):
    id = models.AutoField(primary_key=True)
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='anomalies')
    row_number = models.IntegerField()
    anomaly_type = models.CharField(max_length=255)
    description = models.TextField()
    action_taken = models.TextField()
    requires_approval = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_anomalies'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['batch', 'row_number']
    
    def __str__(self):
        return f"Row {self.row_number}: {self.anomaly_type}"
