from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Group, GroupMember

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name']


class GroupMemberSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = GroupMember
        fields = ['id', 'user', 'joined_at', 'left_at']


class GroupSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'created_by', 'created_at', 'members']
        read_only_fields = ['id', 'created_by', 'created_at']
    
    def get_members(self, obj):
        """Return only active members (left_at is None)"""
        active_members = obj.members.filter(left_at__isnull=True)
        return GroupMemberSerializer(active_members, many=True).data
    
    def create(self, validated_data):
        """Create group and add creator as member"""
        user = self.context['request'].user
        group = Group.objects.create(
            created_by=user,
            **validated_data
        )
        # Add creator as a member
        GroupMember.objects.create(group=group, user=user)
        return group
