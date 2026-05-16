

from django.contrib import admin
from .models import Course, CourseAssignment, Feedback, FeedbackResponse
from .models import Feedback, Course, CourseAssignment, FeedbackResponse, CourseRegistration, FeedbackPeriod



class CourseAssignmentInline(admin.TabularInline):
    model = CourseAssignment
    extra = 1
    fields = ['faculty', 'class_section', 'is_primary']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'course_name', 'get_faculty_names', 'department', 'is_active']
    list_filter = ['department', 'is_active', 'semester']
    search_fields = ['course_code', 'course_name']
    ordering = ['course_code']
    inlines = [CourseAssignmentInline]

    def get_faculty_names(self, obj):
        return obj.get_faculty_names() or '—'
    get_faculty_names.short_description = 'Faculty'


@admin.register(CourseAssignment)
class CourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ['course', 'faculty', 'class_section', 'is_primary', 'assigned_at']
    list_filter = ['is_primary', 'course__department', 'class_section']
    search_fields = ['course__course_code', 'faculty__full_name']
    ordering = ['course__course_code']


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['id', 'course', 'faculty', 'student', 'class_section', 'get_average_rating', 'status', 'feedback_period', 'submitted_at']
    list_filter = ['status', 'is_anonymous', 'class_section', 'submitted_at', 'course__department', 'feedback_period']
    search_fields = ['course__course_code', 'course__course_name', 'student__email', 'faculty__full_name']
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


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display  = ['student', 'course', 'is_confirmed', 'attendance_percentage', 'confirmed_at']
    list_filter   = ['is_confirmed']
    search_fields = ['student__full_name', 'student__student_id', 'course__course_code']
    list_editable = ['attendance_percentage']


@admin.register(FeedbackPeriod)
class FeedbackPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'semester', 'period_type', 'start_date', 'end_date', 'is_active', 'is_open']
    list_filter = ['semester', 'period_type', 'is_active']
    search_fields = ['name', 'semester']
    list_editable = ['is_active']
    ordering = ['-start_date']
