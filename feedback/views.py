from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count

from .models import Feedback, Course, CourseAssignment, FeedbackResponse
from .forms import FeedbackSubmissionForm, FeedbackResponseForm, CourseAssignmentForm, CourseForm
from django.contrib.auth.decorators import user_passes_test
from .models import Feedback, Course, CourseAssignment, FeedbackResponse, CourseRegistration

# STUDENT VIEWS


@login_required
def submit_feedback(request):
    if request.user.role != 'Student':
        messages.error(request, 'Only students can submit feedback.')
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = FeedbackSubmissionForm(request.POST, user=request.user)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.student = request.user
            feedback.save()
            messages.success(request, f'Feedback submitted successfully for {feedback.course.course_code}!')
            return redirect('my_feedback')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeedbackSubmissionForm(user=request.user)

    # Build course → section → faculty mapping for JS
    # Limit mapping to courses available in the form (department-filtered)
    course_qs = form.fields['course'].queryset if 'course' in form.fields else Course.objects.filter(is_active=True)
    assignments = CourseAssignment.objects.filter(
        course__in=course_qs
    ).select_related('course', 'faculty')

    course_faculty_map = {}
    for a in assignments:
        cid = str(a.course_id)
        section = a.class_section or 'ALL'
        if cid not in course_faculty_map:
            course_faculty_map[cid] = {}
        if section not in course_faculty_map[cid]:
            course_faculty_map[cid][section] = []
        course_faculty_map[cid][section].append({'id': a.faculty_id, 'name': a.faculty.full_name})

    context = {
        'form': form,
        'course_faculty_map': course_faculty_map,
        'page_title': 'Submit Course Feedback'
    }
    return render(request, 'feedback/submit_feedback.html', context)


@login_required
def my_feedback(request):
    if request.user.role != 'Student':
        messages.error(request, 'Access denied.')
        return redirect('login')

    feedback_list = Feedback.objects.filter(
        student=request.user
    ).select_related('course', 'faculty')

    context = {
        'feedback_list': feedback_list,
        'page_title': 'My Feedback'
    }
    return render(request, 'feedback/my_feedback.html', context)


@login_required
def feedback_detail(request, feedback_id):
    feedback = get_object_or_404(Feedback, id=feedback_id)

    if request.user.role == 'Student' and feedback.student != request.user:
        messages.error(request, 'You can only view your own feedback.')
        return redirect('my_feedback')

    context = {
        'feedback': feedback,
        'page_title': 'Feedback Detail'
    }
    return render(request, 'feedback/feedback_detail.html', context)


# FACULTY VIEWS


@login_required
def faculty_feedback_list(request):
    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('login')

    feedback_list = Feedback.objects.filter(
        faculty=request.user
    ).select_related('course', 'student').order_by('-submitted_at')

    total_feedback = feedback_list.count()
    pending_response = feedback_list.filter(status='Pending').count()

    avg_ratings = feedback_list.aggregate(
        avg_teaching=Avg('teaching_rating'),
        avg_content=Avg('content_rating'),
        avg_communication=Avg('communication_rating')
    )

    context = {
        'feedback_list': feedback_list,
        'total_feedback': total_feedback,
        'pending_response': pending_response,
        'avg_teaching': round(avg_ratings['avg_teaching'] or 0, 1),
        'avg_content': round(avg_ratings['avg_content'] or 0, 1),
        'avg_communication': round(avg_ratings['avg_communication'] or 0, 1),
        'page_title': 'My Course Feedback'
    }
    return render(request, 'feedback/faculty_feedback_list.html', context)


@login_required
def respond_to_feedback(request, feedback_id):
    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('login')

    feedback = get_object_or_404(Feedback, id=feedback_id)

    if feedback.faculty != request.user:
        messages.error(request, 'You can only respond to feedback assigned to you.')
        return redirect('faculty_feedback_list')

    if hasattr(feedback, 'response'):
        messages.info(request, 'You have already responded to this feedback.')
        return redirect('faculty_feedback_list')

    if request.method == 'POST':
        form = FeedbackResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.feedback = feedback
            response.faculty = request.user
            response.save()

            feedback.status = 'Responded'
            feedback.reviewed_at = timezone.now()
            feedback.save()

            messages.success(request, 'Response submitted successfully!')
            return redirect('faculty_feedback_list')
    else:
        form = FeedbackResponseForm()

    context = {
        'form': form,
        'feedback': feedback,
        'page_title': 'Respond to Feedback'
    }
    return render(request, 'feedback/respond_to_feedback.html', context)


@login_required
def mark_feedback_reviewed(request, feedback_id):
    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    feedback = get_object_or_404(Feedback, id=feedback_id)

    if feedback.faculty != request.user:
        messages.error(request, 'Access denied.')
        return redirect('faculty_feedback_list')

    feedback.status = 'Reviewed'
    feedback.reviewed_at = timezone.now()
    feedback.save()

    messages.success(request, 'Feedback marked as reviewed.')
    return redirect('faculty_feedback_list')


# ADMIN UI (non-Django-admin) - Course Assignments


def admin_required(user):
    return user.is_authenticated and user.role == 'Admin'


@login_required
@user_passes_test(admin_required)
def assignment_list(request):
    assignments = CourseAssignment.objects.select_related('course', 'faculty').order_by('course__course_code', 'class_section')
    context = {
        'assignments': assignments,
        'page_title': 'Course Assignments (Admin)'
    }
    return render(request, 'feedback/admin_assignments_list.html', context)


@login_required
@user_passes_test(admin_required)
def assignment_create(request):
    if request.method == 'POST':
        form = CourseAssignmentForm(request.POST)
        if form.is_valid():
            # Ensure uniqueness constraint handled by model
            form.save()
            messages.success(request, 'Course assignment saved.')
            return redirect('admin_assignments')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseAssignmentForm()

    context = {
        'form': form,
        'page_title': 'Add Course Assignment'
    }
    return render(request, 'feedback/admin_assignment_form.html', context)


@login_required
@user_passes_test(admin_required)
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course created successfully.')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseForm()

    context = {
        'form': form,
        'page_title': 'Add Course'
    }
    return render(request, 'feedback/admin_course_form.html', context)


@login_required
@user_passes_test(admin_required)
def admin_course_list(request):
    """Admin can view and manage all courses."""
    courses = Course.objects.all().order_by('department', 'course_code')

    search = request.GET.get('search', '')
    department = request.GET.get('department', '')
    active_filter = request.GET.get('active', '')

    if search:
        courses = courses.filter(
            course_code__icontains=search
        ) | courses.filter(
            course_name__icontains=search
        )

    if department:
        courses = courses.filter(department=department)

    if active_filter == 'active':
        courses = courses.filter(is_active=True)
    elif active_filter == 'inactive':
        courses = courses.filter(is_active=False)

    # Get unique departments
    departments = Course.objects.values_list('department', flat=True).distinct()

    context = {
        'courses': courses,
        'search': search,
        'department': department,
        'active_filter': active_filter,
        'departments': sorted(departments),
        'page_title': 'Manage Courses'
    }
    return render(request, 'feedback/admin_course_list.html', context)


@login_required
@user_passes_test(admin_required)
def admin_course_delete(request, course_id):
    """Admin can delete a course."""
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        course_name = course.course_code
        course.delete()
        messages.success(request, f'Course {course_name} deleted successfully.')
        return redirect('admin_course_list')

    context = {
        'course': course,
        'page_title': 'Delete Course'
    }
    return render(request, 'feedback/admin_course_delete.html', context)
@login_required
def course_registration_view(request):
    if request.user.role != 'Student':
        messages.error(request, 'Only students can register courses.')
        return redirect('student_dashboard')

    student = request.user

    # Auto-load all active courses for student's department
    active_courses = Course.objects.filter(
        department=student.department,
        is_active=True
    )
    for course in active_courses:
        CourseRegistration.objects.get_or_create(
            student=student,
            course=course,
            defaults={'is_confirmed': False}
        )

    if request.method == 'POST':
        registrations = CourseRegistration.objects.filter(
            student=student,
            course__is_active=True
        )
        for reg in registrations:
            is_checked = request.POST.get(f'course_{reg.id}') == 'on'
            reg.is_confirmed = is_checked
            reg.confirmed_at = timezone.now() if is_checked else None
            reg.save()
        messages.success(request, 'Course registration saved successfully!')
        return redirect('course_registration')

    registrations = CourseRegistration.objects.filter(
        student=student,
        course__is_active=True
    ).select_related('course')

    context = {
        'registrations': registrations,
        'confirmed_count': registrations.filter(is_confirmed=True).count(),
        'total_count': registrations.count(),
        'page_title': 'Course Registration'
    }
    return render(request, 'feedback/course_registration.html', context)
