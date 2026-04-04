

from django.contrib import admin
from .models import Complaint, ComplaintUpdate


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['tracking_id', 'subject', 'student', 'complaint_type', 'status', 'priority', 'assigned_to', 'submitted_at']
    list_filter = ['complaint_type', 'status', 'priority', 'submitted_at']
    search_fields = ['tracking_id', 'subject', 'student__email', 'student__full_name']
    readonly_fields = ['tracking_id', 'submitted_at', 'updated_at']
    ordering = ['-submitted_at']


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_display = ['complaint', 'updated_by', 'status_changed_to', 'created_at']
    list_filter = ['created_at']
    search_fields = ['complaint__tracking_id', 'updated_by__full_name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']