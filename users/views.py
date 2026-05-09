from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms import (
    StudentRegistrationForm,
    LoginForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm,
    AdminUserCreateForm,
    AdminUserEditForm,
    AppointmentForm,
)
from .models import User, Appointment, Notification, Task
from feedback.models import Course, CourseAssignment, Feedback
from complaints.models import Complaint


def home_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    context = {'page_title': 'FeedbackFlow - Login'}
    return render(request, 'users/home.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('student_dashboard')
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account created successfully for {user.full_name}! Please login.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentRegistrationForm()
    context = {'form': form, 'page_title': 'Student Registration'}
    return render(request, 'users/register.html', context)


def login_view(request):
    """
    Unified login view for all users.
    Authenticates user by email and password, then automatically detects
    their role and redirects to the appropriate dashboard.
    """
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.get_short_name()}!')
                    return _redirect_by_role(user)
                else:
                    messages.error(request, 'Your account has been deactivated. Please contact support.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()
    
    context = {
        'form': form,
        'page_title': 'Login to FeedbackFlow',
    }
    return render(request, 'users/login.html', context)


def _redirect_by_role(user):
    role_redirects = {
        'Student': 'student_dashboard',
        'Faculty': 'faculty_dashboard',
        'HOD': 'hod_dashboard',
        'Staff': 'staff_dashboard',
        'Admin': 'admin_dashboard',
    }
    return redirect(role_redirects.get(user.role, 'login'))


@login_required
def logout_view(request):
    user_name = request.user.get_short_name()
    logout(request)
    messages.success(request, f'Goodbye, {user_name}! You have been logged out.')
    return redirect('login')


def password_reset_request(request):
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return _redirect_by_role(request.user)
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            try:
                user = User.objects.get(email=email, is_active=True)
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_url = request.build_absolute_uri(f'/password-reset/confirm/{uid}/{token}/')
                context = {'user': user, 'reset_url': reset_url, 'site_name': 'FeedbackFlow'}
                email_subject = 'Password Reset - FeedbackFlow'
                email_body = render_to_string('users/password_reset_email.html', context)
                send_mail(
                    subject=email_subject,
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=email_body,
                    fail_silently=False,
                )
                messages.success(request, 'Password reset link has been sent to your email. Please check your inbox.')
            except User.DoesNotExist:
                messages.success(request, 'If an account exists with this email, a password reset link has been sent.')
            return redirect('login')
    else:
        form = PasswordResetRequestForm()
    context = {'form': form, 'page_title': 'Reset Password'}
    return render(request, 'users/password_reset_request.html', context)


def password_reset_confirm(request, uidb64, token):
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return _redirect_by_role(request.user)
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                new_password = form.cleaned_data.get('new_password')
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Your password has been reset successfully! Please login with your new password.')
                return redirect('login')
        else:
            form = PasswordResetConfirmForm()
        context = {'form': form, 'validlink': True, 'page_title': 'Set New Password'}
        return render(request, 'users/password_reset_confirm.html', context)
    else:
        messages.error(request, 'Password reset link is invalid or has expired. Please request a new one.')
        return redirect('password_reset_request')


@login_required
def student_dashboard(request):
    if request.user.role != 'Student':
        messages.error(request, 'Access denied. Students only.')
        return redirect('login')
    all_feedback = Feedback.objects.filter(student=request.user)
    total_feedback = all_feedback.count()
    reviewed_count = all_feedback.filter(status__in=['Reviewed', 'Responded']).count()
    pending_feedback = all_feedback.filter(status='Pending').count()
    all_complaints = Complaint.objects.filter(student=request.user)
    total_complaints = all_complaints.count()
    pending_complaints = all_complaints.filter(status='Pending').count()
    recent_feedback = all_feedback.order_by('-submitted_at')[:3]
    recent_complaints = all_complaints.order_by('-submitted_at')[:2]
    tasks = Task.objects.filter(student=request.user)
    pending_tasks = tasks.filter(is_done=False).count()
    done_tasks = tasks.filter(is_done=True).count()
    context = {
        'page_title': 'Student Dashboard',
        'user': request.user,
        'total_submissions': total_feedback + total_complaints,
        'total_feedback': total_feedback,
        'total_complaints': total_complaints,
        'reviewed_count': reviewed_count,
        'pending_count': pending_feedback + pending_complaints,
        'active_complaints': all_complaints.exclude(status='Resolved').count(),
        'recent_feedback': recent_feedback,
        'recent_complaints': recent_complaints,
        'has_submissions': (total_feedback + total_complaints) > 0,
        'pending_tasks': pending_tasks,
        'done_tasks': done_tasks,
    }
    return render(request, 'users/student_dashboard.html', context)


@login_required
def faculty_dashboard(request):
    if request.user.role != 'Faculty':
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('login')
    from datetime import timedelta
    from django.utils import timezone
    all_feedback = Feedback.objects.filter(faculty=request.user)
    courses = Course.objects.filter(assignments__faculty=request.user, is_active=True).distinct()
    total_feedback = all_feedback.count()
    pending_response = all_feedback.filter(status='Pending').count()
    avg_ratings = all_feedback.aggregate(avg_all=Avg('teaching_rating'))
    average_rating = round(avg_ratings['avg_all'] or 0, 1)
    week_ago = timezone.now() - timedelta(days=7)
    this_week_feedback = all_feedback.filter(submitted_at__gte=week_ago).count()
    recent_feedback = all_feedback.order_by('-submitted_at')[:5]
    context = {
        'page_title': 'Faculty Dashboard',
        'user': request.user,
        'total_feedback': total_feedback,
        'pending_response': pending_response,
        'average_rating': average_rating,
        'courses_count': courses.count(),
        'this_week_feedback': this_week_feedback,
        'recent_feedback': recent_feedback,
        'has_feedback': total_feedback > 0,
    }
    return render(request, 'users/faculty_dashboard.html', context)


@login_required
def hod_dashboard(request):
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied. HOD only.')
        return redirect('login')
    all_complaints = Complaint.objects.filter(assigned_to=request.user)
    total_complaints = all_complaints.count()
    pending_complaints = all_complaints.filter(status='Pending').count()
    resolved_complaints = all_complaints.filter(status='Resolved').count()
    escalated_complaints = all_complaints.filter(status='Escalated').count()
    faculty_count = User.objects.filter(role='Faculty', department=request.user.department).count()
    recent_complaints = all_complaints.order_by('-submitted_at')[:5]
    context = {
        'page_title': 'HOD Dashboard',
        'user': request.user,
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'resolved_complaints': resolved_complaints,
        'escalated_complaints': escalated_complaints,
        'faculty_count': faculty_count,
        'recent_complaints': recent_complaints,
        'has_complaints': total_complaints > 0,
    }
    return render(request, 'users/hod_dashboard.html', context)


@login_required
def staff_dashboard(request):
    if request.user.role != 'Staff':
        messages.error(request, 'Access denied. Staff only.')
        return redirect('login')
    all_complaints = Complaint.objects.filter(assigned_to=request.user)
    assigned_complaints = all_complaints.count()
    pending_complaints = all_complaints.filter(status='Pending').count()
    in_progress_complaints = all_complaints.filter(status='Under Investigation').count()
    resolved_complaints = all_complaints.filter(status='Resolved').count()
    recent_complaints = all_complaints.order_by('-submitted_at')[:5]
    context = {
        'page_title': 'Staff Dashboard',
        'user': request.user,
        'assigned_complaints': assigned_complaints,
        'pending_complaints': pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
        'avg_resolution_time': 0,
        'recent_complaints': recent_complaints,
        'has_complaints': assigned_complaints > 0,
    }
    return render(request, 'users/staff_dashboard.html', context)


@login_required
def admin_dashboard(request):
    if request.user.role != 'Admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('login')
    user_stats = User.objects.values('role').annotate(count=Count('id'))
    role_counts = {stat['role']: stat['count'] for stat in user_stats}
    total_feedback = Feedback.objects.count()
    total_complaints = Complaint.objects.count()
    pending_complaints = Complaint.objects.filter(status='Pending').count()
    context = {
        'page_title': 'Admin Dashboard',
        'user': request.user,
        'total_users': User.objects.count(),
        'total_courses': Course.objects.count(),
        'total_assignments': CourseAssignment.objects.count(),
        'student_count': role_counts.get('Student', 0),
        'faculty_count': role_counts.get('Faculty', 0),
        'hod_count': role_counts.get('HOD', 0),
        'staff_count': role_counts.get('Staff', 0),
        'admin_count': role_counts.get('Admin', 0),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
        'department_stats': User.objects.filter(department__isnull=False).values('department').annotate(count=Count('id')),
        'total_feedback': total_feedback,
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'recent_users': User.objects.order_by('-created_at')[:5],
    }
    return render(request, 'users/admin_dashboard.html', context)


@login_required
def admin_user_list(request):
    if request.user.role != 'Admin':
        return redirect('login')
    users = User.objects.all().order_by('-created_at')
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    dept_filter = request.GET.get('department', '')
    if search:
        users = users.filter(full_name__icontains=search) | users.filter(email__icontains=search)
    if role_filter:
        users = users.filter(role=role_filter)
    if dept_filter:
        users = users.filter(department=dept_filter)
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    context = {
        'users': users,
        'search': search,
        'role_filter': role_filter,
        'dept_filter': dept_filter,
        'status_filter': request.GET.get('status', ''),
        'roles': User.ROLE_CHOICES,
        'departments': User.DEPARTMENT_CHOICES,
        'role_choices': User.ROLE_CHOICES,
        'department_choices': User.DEPARTMENT_CHOICES,
    }
    return render(request, 'users/admin_user_list.html', context)


@login_required
def admin_user_create(request):
    if request.user.role != 'Admin':
        return redirect('login')
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'User created successfully.')
            return redirect('admin_user_list')
    else:
        form = AdminUserCreateForm()
    return render(request, 'users/admin_user_form.html', {'form': form, 'action': 'Create'})


@login_required
def admin_user_edit(request, user_id):
    if request.user.role != 'Admin':
        return redirect('login')
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, f'{target_user.full_name} updated successfully.')
            return redirect('admin_user_list')
    else:
        form = AdminUserEditForm(instance=target_user)
    return render(request, 'users/admin_user_form.html', {'form': form, 'action': 'Edit', 'target_user': target_user})


@login_required
def admin_user_delete(request, user_id):
    if request.user.role != 'Admin':
        return redirect('login')
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('admin_user_list')
    if request.method == 'POST':
        target_user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('admin_user_list')
    return render(request, 'users/admin_user_delete.html', {'target_user': target_user})


@login_required
def admin_user_toggle_active(request, user_id):
    if request.user.role != 'Admin':
        return redirect('login')
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, 'You cannot change your own active status.')
        return redirect('admin_user_list')
    target_user.is_active = not target_user.is_active
    target_user.save()
    status = 'activated' if target_user.is_active else 'deactivated'
    messages.success(request, f'{target_user.full_name} has been {status}.')
    return redirect('admin_user_list')


@login_required
def hod_faculty_list(request):
    if request.user.role != 'HOD':
        return redirect('login')
    faculty_list = User.objects.filter(role='Faculty', department=request.user.department).order_by('full_name')
    context = {'faculty_list': faculty_list, 'page_title': 'Faculty List'}
    return render(request, 'users/hod_faculty_list.html', context)


@login_required
def feedback_reports(request):
    if request.user.role not in ['Admin', 'HOD']:
        return redirect('login')
    dept_filter = request.GET.get('department', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    course_filter = request.GET.get('course', '')
    feedbacks = Feedback.objects.all()
    if request.user.role == 'HOD':
        feedbacks = feedbacks.filter(course__department=request.user.department)
    if dept_filter:
        feedbacks = feedbacks.filter(course__department=dept_filter)
    if date_from:
        feedbacks = feedbacks.filter(submitted_at__date__gte=date_from)
    if date_to:
        feedbacks = feedbacks.filter(submitted_at__date__lte=date_to)
    if course_filter:
        feedbacks = feedbacks.filter(course_id=course_filter)
    avg_ratings = feedbacks.aggregate(
        avg_teaching=Avg('teaching_rating'),
        avg_content=Avg('content_rating'),
        avg_communication=Avg('communication_rating'),
    )
    avg_teaching = round(avg_ratings['avg_teaching'] or 0, 1)
    avg_content = round(avg_ratings['avg_content'] or 0, 1)
    avg_communication = round(avg_ratings['avg_communication'] or 0, 1)
    overall_avg = round((avg_teaching + avg_content + avg_communication) / 3, 1) if feedbacks.exists() else 0
    course_stats = feedbacks.values(
        'course__course_code', 'course__course_name', 'faculty__full_name'
    ).annotate(
        count=Count('id'),
        avg_teaching=Avg('teaching_rating'),
        avg_content=Avg('content_rating'),
        avg_communication=Avg('communication_rating'),
    ).order_by('-count')
    status_counts = {
        'Pending': feedbacks.filter(status='Pending').count(),
        'Reviewed': feedbacks.filter(status='Reviewed').count(),
        'Responded': feedbacks.filter(status='Responded').count(),
    }
    context = {
        'feedbacks': feedbacks,
        'course_stats': course_stats,
        'total_feedback': feedbacks.count(),
        'avg_teaching': avg_teaching,
        'avg_content': avg_content,
        'avg_communication': avg_communication,
        'overall_avg': overall_avg,
        'status_counts': status_counts,
        'dept_filter': dept_filter,
        'date_from': date_from,
        'date_to': date_to,
        'course_filter': course_filter,
        'departments': User.DEPARTMENT_CHOICES,
        'department_choices': User.DEPARTMENT_CHOICES,
        'courses': Course.objects.filter(is_active=True).order_by('course_code'),
    }
    return render(request, 'users/feedback_reports.html', context)


@login_required
def appointment_view(request):
    if request.user.role != 'Student':
        messages.error(request, 'Only students can book appointments.')
        return redirect('student_dashboard')
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            Appointment.objects.create(
                student=request.user,
                name=form.cleaned_data['name'],
                roll_number=form.cleaned_data['roll_number'],
                department=form.cleaned_data['department'],
                appointment_with=form.cleaned_data['appointment_with'],
                incident_type=form.cleaned_data['incident_type'],
                description=form.cleaned_data['description'],
            )
            admins = User.objects.filter(role='Admin')
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    title=f'New Appointment Request from {request.user.full_name}',
                    message=f'{request.user.full_name} (ID: {request.user.student_id}) has requested an appointment with {form.cleaned_data["appointment_with"]}.',
                    notification_type='appointment',
                    link='/appointment/',
                )
            messages.success(request, 'Appointment submitted successfully! You will be notified once approved.')
            return redirect('appointment')
    else:
        form = AppointmentForm(initial={
            'name': request.user.full_name,
            'roll_number': request.user.student_id,
            'department': request.user.department,
        })
    return render(request, 'users/appointment.html', {'form': form})


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'users/notifications.html', {
        'notifications': notifications,
        'page_title': 'Notifications',
    })


@login_required
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect('notifications')


@login_required
def task_list(request):
    if request.user.role != 'Student':
        return redirect('home')
    tasks = Task.objects.filter(student=request.user)
    daily  = tasks.filter(task_type='Daily')
    weekly = tasks.filter(task_type='Weekly')
    return render(request, 'users/task_list.html', {
        'daily': daily,
        'weekly': weekly,
    })


@login_required
@require_POST
def task_add(request):
    if request.user.role != 'Student':
        return redirect('home')
    title       = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    task_type   = request.POST.get('task_type', 'Daily')
    priority    = request.POST.get('priority', 'Medium')
    due_date    = request.POST.get('due_date') or None
    if title:
        Task.objects.create(
            student=request.user,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            due_date=due_date,
        )
        messages.success(request, 'Task added successfully.')
    return redirect('task_list')


@login_required
def task_toggle(request, task_id):
    task = get_object_or_404(Task, id=task_id, student=request.user)
    task.is_done = not task.is_done
    task.save()
    return redirect('task_list')


@login_required
def task_delete(request, task_id):
    task = get_object_or_404(Task, id=task_id, student=request.user)
    task.delete()
    messages.success(request, 'Task deleted.')
    return redirect('task_list')