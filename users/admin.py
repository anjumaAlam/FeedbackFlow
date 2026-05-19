# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Appointment, Notification, Announcement




@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""

    list_display = ['email', 'full_name', 'role', 'department', 'is_active', 'created_at']
    list_filter = ['role', 'department', 'is_active', 'created_at']
    search_fields = ['email', 'full_name', 'student_id']
    ordering = ['-created_at']

    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'student_id', 'department')
        }),
        ('Permissions', {
            'fields': ('role', 'committee_type', 'is_active', 'is_staff', 'is_superuser')  # ← added
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'committee_type', 'department', 'student_id', 'password1', 'password2'),  # ← added
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login']

    @admin.register(Appointment)
    class AppointmentAdmin(admin.ModelAdmin):
        list_display = ['name', 'roll_number', 'department', 'appointment_with', 'incident_type', 'status',
                        'created_at']
        list_filter = ['status', 'department', 'appointment_with', 'incident_type']
        search_fields = ['name', 'roll_number']
        ordering = ['-created_at']

    @admin.register(Notification)
    class NotificationAdmin(admin.ModelAdmin):
        list_display = ['recipient', 'title', 'notification_type', 'is_read', 'created_at']
        list_filter = ['notification_type', 'is_read']
        search_fields = ['recipient__full_name', 'title']
        ordering = ['-created_at']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'target_roles', 'is_active', 'created_by', 'created_at', 'expires_at']
    list_filter = ['priority', 'is_active']
    search_fields = ['title', 'content']
    list_editable = ['is_active']
    ordering = ['-created_at']