from django.contrib import admin
from .models import Group, GroupMember


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'created_by__email']
    readonly_fields = ['id', 'created_at']
    fieldsets = (
        ('Group Info', {'fields': ('id', 'name', 'created_by')}),
        ('Meta', {'fields': ('created_at',)}),
    )


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'joined_at', 'left_at']
    list_filter = ['group', 'joined_at', 'left_at']
    search_fields = ['user__email', 'group__name']
    readonly_fields = ['id', 'joined_at']
    fieldsets = (
        ('Membership', {'fields': ('id', 'group', 'user')}),
        ('Timeline', {'fields': ('joined_at', 'left_at')}),
    )
