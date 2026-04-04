

from django.contrib import admin
from .models import Course, Feedback, FeedbackResponse


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'course_name', 'faculty', 'department', 'is_active']
    list_filter = ['department', 'is_active', 'semester']
    search_fields = ['course_code', 'course_name', 'faculty__full_name']
    ordering = ['course_code']


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['id', 'course', 'student', 'get_average_rating', 'status', 'is_anonymous', 'submitted_at']
    list_filter = ['status', 'is_anonymous', 'submitted_at', 'course__department']
    search_fields = ['course__course_code', 'course__course_name', 'student__email']
    readonly_fields = ['submitted_at', 'reviewed_at']
    ordering = ['-submitted_at']

    def get_average_rating(self, obj):
        return obj.get_average_rating()

    get_average_rating.short_description = 'Avg Rating'


@admin.register(FeedbackResponse)
class FeedbackResponseAdmin(admin.ModelAdmin):
    list_display = ['feedback', 'faculty', 'responded_at']
    search_fields = ['feedback__course__course_code', 'faculty__full_name']
    readonly_fields = ['responded_at']
    ordering = ['-responded_at']