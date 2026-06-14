from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'created_at']
    list_filter = ['created_at']
    search_fields = ['email', 'name']
    readonly_fields = ['id', 'created_at']
    fieldsets = (
        ('Account', {'fields': ('id', 'email', 'name', 'password')}),
        ('Meta', {'fields': ('created_at',)}),
    )
