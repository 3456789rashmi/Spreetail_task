from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import ImportBatch, ImportAnomaly
from .parser import CSVImporter

User = __import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model()


class ImportCSVView(generics.GenericAPIView):
    """
    Upload and import CSV file for a group.
    POST: upload CSV file and run importer
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        group_id = request.data.get('group_id')
        
        if not file_obj:
            return Response(
                {'detail': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not group_id:
            return Response(
                {'detail': 'group_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Import Group here to avoid circular imports
        from groups.models import Group, GroupMember
        
        # Verify user is a member of this group
        group = get_object_or_404(Group, id=group_id)
        if not GroupMember.objects.filter(group=group, user=request.user, left_at__isnull=True).exists():
            return Response(
                {'detail': 'You are not a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create import batch
        batch = ImportBatch.objects.create(
            filename=file_obj.name,
            status='pending',
            imported_by=request.user
        )
        
        # Run importer
        importer = CSVImporter(file_obj, batch, group, request.user)
        report = importer.import_csv()
        
        return Response(report, status=status.HTTP_201_CREATED)


class ImportReportView(generics.GenericAPIView):
    """
    Get import report for a batch.
    GET: retrieve batch details and anomalies
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        batch_id = self.kwargs.get('batch_id')
        batch = get_object_or_404(ImportBatch, id=batch_id)
        
        # Verify user imported this batch
        if batch.imported_by != request.user:
            return Response(
                {'detail': 'You do not have permission to view this batch'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        anomalies = batch.anomalies.all()
        
        return Response({
            'batch_id': batch.id,
            'filename': batch.filename,
            'status': batch.status,
            'imported_at': batch.imported_at,
            'imported_by': batch.imported_by.email,
            'total_anomalies': anomalies.count(),
            'anomalies_requiring_approval': anomalies.filter(requires_approval=True).count(),
            'anomalies': [
                {
                    'id': a.id,
                    'row_number': a.row_number,
                    'anomaly_type': a.anomaly_type,
                    'description': a.description,
                    'action_taken': a.action_taken,
                    'requires_approval': a.requires_approval,
                    'is_approved': a.is_approved,
                    'approved_by': a.approved_by.email if a.approved_by else None,
                    'approved_at': a.approved_at
                }
                for a in anomalies
            ]
        })


class ApproveAnomalyView(generics.GenericAPIView):
    """
    Approve a flagged anomaly (for Meera's approval flow).
    POST: approve an anomaly
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        anomaly_id = self.kwargs.get('anomaly_id')
        anomaly = get_object_or_404(ImportAnomaly, id=anomaly_id)
        
        if not anomaly.requires_approval:
            return Response(
                {'detail': 'This anomaly does not require approval'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if anomaly.is_approved:
            return Response(
                {'detail': 'This anomaly has already been approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Approve anomaly
        anomaly.is_approved = True
        anomaly.approved_by = request.user
        anomaly.approved_at = timezone.now()
        anomaly.save()
        
        return Response({
            'id': anomaly.id,
            'anomaly_type': anomaly.anomaly_type,
            'is_approved': anomaly.is_approved,
            'approved_by': anomaly.approved_by.email,
            'approved_at': anomaly.approved_at
        })
