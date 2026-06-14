from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Group, GroupMember
from .serializers import GroupSerializer, GroupMemberSerializer

User = get_user_model()


class GroupListCreateView(generics.ListCreateAPIView):
    """
    List all groups the user belongs to, or create a new group.
    """
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return only groups where the user is an active member"""
        user = self.request.user
        group_ids = GroupMember.objects.filter(
            user=user,
            left_at__isnull=True
        ).values_list('group_id', flat=True)
        return Group.objects.filter(id__in=group_ids)
    
    def perform_create(self, serializer):
        serializer.save()


class GroupDetailView(generics.RetrieveAPIView):
    """
    Get a single group with all its active members.
    """
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only allow viewing groups user is a member of"""
        user = self.request.user
        group_ids = GroupMember.objects.filter(
            user=user,
            left_at__isnull=True
        ).values_list('group_id', flat=True)
        return Group.objects.filter(id__in=group_ids)


class AddMemberView(generics.CreateAPIView):
    """
    Add a user to a group by email (POST).
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        group_id = self.kwargs.get('pk')
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'detail': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user is a member of this group
        group = get_object_or_404(Group, id=group_id)
        if not GroupMember.objects.filter(group=group, user=request.user, left_at__isnull=True).exists():
            return Response(
                {'detail': 'You are not a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User with this email not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is already a member
        member, created = GroupMember.objects.get_or_create(
            group=group,
            user=user
        )
        
        if not created and member.left_at is None:
            return Response(
                {'detail': 'User is already a member of this group'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If they left before, re-add them
        if member.left_at is not None:
            member.left_at = None
            member.save()
        
        serializer = GroupMemberSerializer(member)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RemoveMemberView(generics.DestroyAPIView):
    """
    Remove a user from a group by setting left_at = today (DELETE).
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, *args, **kwargs):
        group_id = self.kwargs.get('pk')
        user_id = self.kwargs.get('user_id')
        
        group = get_object_or_404(Group, id=group_id)
        
        # Verify requester is a member of this group
        if not GroupMember.objects.filter(group=group, user=request.user, left_at__isnull=True).exists():
            return Response(
                {'detail': 'You are not a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the member to remove
        member = get_object_or_404(GroupMember, group=group, user_id=user_id)
        
        if member.left_at is not None:
            return Response(
                {'detail': 'User is not currently a member of this group'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        member.left_at = timezone.now()
        member.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
