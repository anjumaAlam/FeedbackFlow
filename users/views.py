from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
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


# ── UNIFIED LOGIN — one page, all roles ──────────────────────────────────────
def unified_login_view(request):
    """
    Single login page for ALL roles.
    No role selection needed — system detects role from credentials
    and redirects automatically.
    """
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email    = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user     = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.get_short_name()}!')
                    return _redirect_by_role(user)
                else:
                    messages.error(request, 'Your account has been deactivated. Please contact admin.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {
        'form':       form,
        'page_title': 'Login - FeedbackFlow',
    })


# ── ROLE-SPECIFIC LOGIN (kept for backward compat) ───────────────────────────
def login_view(request, role='student', allowed_roles=None):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    role_map = {
        'student':   'Student',
        'faculty':   'Faculty',
        'staff':     'Staff',
        'dao':       'DAO',
        'admin':     'Admin',
        'hod':       'HOD',
        'committee': 'Committee',
    }

    primary_role = role_map.get(role.lower(), 'Student')
    if allowed_roles is None:
        allowed_roles = [primary_role]
    else:
        allowed_roles = [role_map.get(r.lower(), r) for r in allowed_roles]

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email    = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user     = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_active:
                    if user.role not in allowed_roles:
                        roles_str = ' or '.join(allowed_roles)
                        messages.error(request, f'This account is registered as {user.role}. This page is for {roles_str} login.')
                    else:
                        login(request, user)
                        messages.success(request, f'Welcome back, {user.get_short_name()}!')
                        return _redirect_by_role(user)
                else:
                    messages.error(request, 'Your account has been deactivated.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()

    context = {
        'form':          form,
        'page_title':    f'{primary_role} Login',
        'role':          role,
        'role_display':  primary_role,
        'allowed_roles': allowed_roles,
    }
    return render(request, 'users/login.html', context)


def student_login_view(request):
    return login_view(request, role='student')

def faculty_login_view(request):
    return login_view(request, role='faculty', allowed_roles=['Faculty', 'HOD'])

def staff_login_view(request):
    return login_view(request, role='staff')

def dao_login_view(request):
    return login_view(request, role='dao', allowed_roles=['DAO'])

def admin_login_view(request):
    return login_view(request, role='admin')

def committee_login_view(request):
    return login_view(request, role='committee', allowed_roles=['Committee'])


def _redirect_by_role(user):
    role_redirects = {
        'Student':   'student_dashboard',
        'Faculty':   'faculty_dashboard',
        'HOD':       'hod_dashboard',
        'Staff':     'staff_dashboard',
        'DAO':       'dao_dashboard',
        'Admin':     'admin_dashboard',
        'Committee': 'committee_dashboard',
    }
    return redirect(role_redirects.get(user.role, 'login'))


@login_required
def logout_view(request):
    user_name = request.user.get_short_name()
    logout(request)
    messages.success(request, f'Goodbye, {user_name}! You have been logged out.')
    return redirect('login')


# ── PASSWORD RESET ────────────────────────────────────────────────────────────

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
                messages.success(request, 'Password reset link has been sent to your email.')
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
        uid  = force_str(urlsafe_base64_decode(uidb64))
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
                messages.success(request, 'Password reset successfully! Please login.')
                return redirect('login')
        else:
            form = PasswordResetConfirmForm()
        context = {'form': form, 'validlink': True, 'page_title': 'Set New Password'}
        return render(request, 'users/password_reset_confirm.html', context)
    else:
        messages.error(request, 'Password reset link is invalid or has expired.')
        return redirect('password_reset_request')


# ── STUDENT ───────────────────────────────────────────────────────────────────

@login_required
def student_dashboard(request):
    if request.user.role != 'Student':
        messages.error(request, 'Access denied. Students only.')
        return redirect('login')

    all_feedback       = Feedback.objects.filter(student=request.user)
    total_feedback     = all_feedback.count()
    reviewed_count     = all_feedback.filter(status__in=['Reviewed', 'Responded']).count()
    pending_feedback   = all_feedback.filter(status='Pending').count()
    all_complaints     = Complaint.objects.filter(student=request.user)
    total_complaints   = all_complaints.count()
    pending_complaints = all_complaints.filter(status='Pending').count()
    recent_feedback    = all_feedback.order_by('-submitted_at')[:3]
    recent_complaints  = all_complaints.order_by('-submitted_at')[:2]
    tasks              = Task.objects.filter(student=request.user)
    pending_tasks      = tasks.filter(is_done=False).count()
    done_tasks         = tasks.filter(is_done=True).count()
    recent_appointments = Appointment.objects.filter(
        student=request.user
    ).order_by('-created_at')[:3]



    from complaints.models import ClarificationRequest
    pending_clarifications = ClarificationRequest.objects.filter(
        target_user=request.user, status='Pending'
    ).count()

    context = {
        'page_title':              'Student Dashboard',
        'user':                    request.user,
        'total_submissions':       total_feedback + total_complaints,
        'total_feedback':          total_feedback,
        'total_complaints':        total_complaints,
        'reviewed_count':          reviewed_count,
        'pending_count':           pending_feedback + pending_complaints,
        'active_complaints':       all_complaints.exclude(status='Resolved').count(),
        'recent_feedback':         recent_feedback,
        'recent_complaints':       recent_complaints,
        'has_submissions':         (total_feedback + total_complaints) > 0,
        'pending_tasks':           pending_tasks,
        'done_tasks':              done_tasks,
        'recent_appointments':     recent_appointments,
        'pending_clarifications':  pending_clarifications,

    }
    return render(request, 'users/student_dashboard.html', context)

# ── FACULTY ───────────────────────────────────────────────────────────────────

@login_required
def faculty_dashboard(request):
    if request.user.role != 'Faculty':
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('login')
    from datetime import timedelta
    from django.utils import timezone
    all_feedback       = Feedback.objects.filter(faculty=request.user)
    courses            = Course.objects.filter(assignments__faculty=request.user, is_active=True).distinct()
    total_feedback     = all_feedback.count()
    pending_response   = all_feedback.filter(status='Pending').count()
    avg_ratings        = all_feedback.aggregate(avg_all=Avg('teaching_rating'))
    average_rating     = round(avg_ratings['avg_all'] or 0, 1)
    week_ago           = timezone.now() - timedelta(days=7)
    this_week_feedback = all_feedback.filter(submitted_at__gte=week_ago).count()
    recent_feedback    = all_feedback.order_by('-submitted_at')[:5]

    from complaints.models import ClarificationRequest
    pending_clarifications = ClarificationRequest.objects.filter(
        target_user=request.user, status='Pending'
    ).count()


    context = {
        'page_title':         'Faculty Dashboard',
        'user':               request.user,
        'total_feedback':     total_feedback,
        'pending_response':   pending_response,
        'average_rating':     average_rating,
        'courses_count':      courses.count(),
        'this_week_feedback': this_week_feedback,
        'recent_feedback':    recent_feedback,
        'has_feedback':       total_feedback > 0,
    }
    return render(request, 'users/faculty_dashboard.html', context)


# ── HOD ───────────────────────────────────────────────────────────────────────

@login_required
def hod_dashboard(request):
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied. HOD only.')
        return redirect('login')
    all_complaints       = Complaint.objects.filter(assigned_to=request.user)
    total_complaints     = all_complaints.count()
    pending_complaints   = all_complaints.filter(status='Pending').count()
    resolved_complaints  = all_complaints.filter(status='Resolved').count()
    escalated_complaints = all_complaints.filter(status='Escalated').count()
    faculty_count        = User.objects.filter(role='Faculty', department=request.user.department).count()
    recent_complaints    = all_complaints.order_by('-submitted_at')[:5]
    context = {
        'page_title':            'HOD Dashboard',
        'user':                  request.user,
        'total_complaints':      total_complaints,
        'pending_complaints':    pending_complaints,
        'resolved_complaints':   resolved_complaints,
        'escalated_complaints':  escalated_complaints,
        'faculty_count':         faculty_count,
        'recent_complaints':     recent_complaints,
        'has_complaints':        total_complaints > 0,
    }
    return render(request, 'users/hod_dashboard.html', context)


# ── STAFF ─────────────────────────────────────────────────────────────────────

@login_required
def staff_dashboard(request):
    if request.user.role != 'Staff':
        messages.error(request, 'Access denied. Staff only.')
        return redirect('login')

    from complaints.models import Complaint
    from django.utils import timezone

    all_complaints         = Complaint.objects.filter(assigned_to=request.user)
    assigned_complaints    = all_complaints.count()
    pending_complaints     = all_complaints.filter(status='Pending').count()
    in_progress_complaints = all_complaints.filter(status='Under Investigation').count()
    resolved_complaints    = all_complaints.filter(status='Resolved').count()
    recent_complaints      = all_complaints.order_by('-submitted_at')[:5]

    # Calculate average resolution time in hours
    resolved = all_complaints.filter(
        status='Resolved',
        resolved_at__isnull=False
    )
    if resolved.exists():
        total_hours = 0
        count = 0
        for c in resolved:
            if c.resolved_at and c.submitted_at:
                diff = c.resolved_at - c.submitted_at
                total_hours += diff.total_seconds() / 3600
                count += 1
        avg_hours = total_hours / count if count > 0 else 0
        if avg_hours < 1:
            avg_resolution_time = f"{round(avg_hours * 60):.0f} minutes"
        else:
            avg_resolution_time = f"{round(avg_hours, 1)} hours"
    else:
        avg_resolution_time = 0

    context = {
        'page_title':             'Staff Dashboard',
        'user':                   request.user,
        'assigned_complaints':    assigned_complaints,
        'pending_complaints':     pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints':    resolved_complaints,
        'avg_resolution_time':    avg_resolution_time,
        'recent_complaints':      recent_complaints,
        'has_complaints':         assigned_complaints > 0,
    }
    return render(request, 'users/staff_dashboard.html', context)



# ── ADMIN ─────────────────────────────────────────────────────────────────────

@login_required
def admin_dashboard(request):
    if request.user.role != 'Admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('login')
    user_stats         = User.objects.values('role').annotate(count=Count('id'))
    role_counts        = {stat['role']: stat['count'] for stat in user_stats}
    total_feedback     = Feedback.objects.count()
    total_complaints   = Complaint.objects.count()
    pending_complaints = Complaint.objects.filter(status='Pending').count()
    context = {
        'page_title':         'Admin Dashboard',
        'user':               request.user,
        'total_users':        User.objects.count(),
        'total_courses':      Course.objects.count(),
        'total_assignments':  CourseAssignment.objects.count(),
        'student_count':      role_counts.get('Student', 0),
        'faculty_count':      role_counts.get('Faculty', 0),
        'hod_count':          role_counts.get('HOD', 0),
        'staff_count':        role_counts.get('Staff', 0),
        'admin_count':        role_counts.get('Admin', 0),
        'active_users':       User.objects.filter(is_active=True).count(),
        'inactive_users':     User.objects.filter(is_active=False).count(),
        'department_stats':   User.objects.filter(department__isnull=False).values('department').annotate(count=Count('id')),
        'total_feedback':     total_feedback,
        'total_complaints':   total_complaints,
        'pending_complaints': pending_complaints,
        'recent_users':       User.objects.order_by('-created_at')[:5],
    }
    return render(request, 'users/admin_dashboard.html', context)


@login_required
def admin_user_list(request):
    if request.user.role != 'Admin':
        return redirect('login')
    users         = User.objects.all().order_by('-created_at')
    search        = request.GET.get('q', '')
    role_filter   = request.GET.get('role', '')
    dept_filter   = request.GET.get('department', '')
    status_filter = request.GET.get('status', '')
    if search:
        users = users.filter(full_name__icontains=search) | users.filter(email__icontains=search)
    if role_filter:
        users = users.filter(role=role_filter)
    if dept_filter:
        users = users.filter(department=dept_filter)
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    context = {
        'users':              users,
        'search_query':       search,
        'role_filter':        role_filter,
        'dept_filter':        dept_filter,
        'status_filter':      status_filter,
        'roles':              User.ROLE_CHOICES,
        'departments':        User.DEPARTMENT_CHOICES,
        'role_choices':       User.ROLE_CHOICES,
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
    dept_filter    = request.GET.get('department', '')
    date_from      = request.GET.get('date_from', '')
    date_to        = request.GET.get('date_to', '')
    course_filter  = request.GET.get('course', '')
    faculty_filter = request.GET.get('faculty', '')
    semester_filter = request.GET.get('semester', '')  # FR 7.2: semester filter
    feedbacks      = Feedback.objects.all()
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
    if faculty_filter:
        feedbacks = feedbacks.filter(faculty_id=faculty_filter)
    if semester_filter:
        feedbacks = feedbacks.filter(course__semester=semester_filter)
    avg_ratings = feedbacks.aggregate(
        avg_teaching=Avg('teaching_rating'),
        avg_content=Avg('content_rating'),
        avg_communication=Avg('communication_rating'),
    )
    avg_teaching      = round(avg_ratings['avg_teaching'] or 0, 1)
    avg_content       = round(avg_ratings['avg_content'] or 0, 1)
    avg_communication = round(avg_ratings['avg_communication'] or 0, 1)
    overall_avg       = round((avg_teaching + avg_content + avg_communication) / 3, 1) if feedbacks.exists() else 0
    course_stats = feedbacks.values(
        'course__course_code', 'course__course_name', 'faculty__full_name'
    ).annotate(
        count=Count('id'),
        avg_teaching=Avg('teaching_rating'),
        avg_content=Avg('content_rating'),
        avg_communication=Avg('communication_rating'),
    ).order_by('-count')
    status_counts = {
        'Pending':   feedbacks.filter(status='Pending').count(),
        'Reviewed':  feedbacks.filter(status='Reviewed').count(),
        'Responded': feedbacks.filter(status='Responded').count(),
    }

    # FR 7.2: Semester-wise comparison data
    all_fb = Feedback.objects.all()
    if request.user.role == 'HOD':
        all_fb = all_fb.filter(course__department=request.user.department)
    semester_comparison = (
        all_fb
        .exclude(course__semester__isnull=True)
        .exclude(course__semester='')
        .values('course__semester')
        .annotate(
            count=Count('id'),
            avg_teaching=Avg('teaching_rating'),
            avg_content=Avg('content_rating'),
            avg_communication=Avg('communication_rating'),
        )
        .order_by('course__semester')
    )

    # Available semesters for filter dropdown
    semesters = (
        Course.objects.exclude(semester__isnull=True)
        .exclude(semester='')
        .values_list('semester', flat=True)
        .distinct()
        .order_by('semester')
    )

    context = {
        'feedbacks':            feedbacks,
        'course_stats':         course_stats,
        'total_feedback':       feedbacks.count(),
        'avg_teaching':         avg_teaching,
        'avg_content':          avg_content,
        'avg_communication':    avg_communication,
        'overall_avg':          overall_avg,
        'status_counts':        status_counts,
        'dept_filter':          dept_filter,
        'date_from':            date_from,
        'date_to':              date_to,
        'course_filter':        course_filter,
        'faculty_filter':       faculty_filter,
        'semester_filter':      semester_filter,
        'departments':          User.DEPARTMENT_CHOICES,
        'department_choices':   User.DEPARTMENT_CHOICES,
        'courses':              (Course.objects.filter(department=request.user.department, is_active=True).order_by('course_code') if request.user.role == 'HOD' else Course.objects.filter(is_active=True).order_by('course_code')),
        'faculty_list':         (User.objects.filter(role='Faculty', department=request.user.department) if request.user.role == 'HOD' else User.objects.filter(role='Faculty').order_by('full_name')),
        'semesters':            semesters,
        'semester_comparison':  semester_comparison,
    }
    return render(request, 'users/feedback_reports.html', context)


# ── FEEDBACK ANALYTICS (Plotly Charts) ────────────────────────────────────────

@login_required
def feedback_analytics(request):
    """
    Graphical reports page with 5 interactive Plotly charts + faculty-specific analytics.
    HOD sees only their department's faculty; Admin sees all.
    """
    if request.user.role not in ['Admin', 'HOD']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    import plotly.graph_objects as go
    from plotly.offline import plot
    from django.db.models.functions import TruncMonth

    # ── Filters ───────────────────────────────────────────────────────────
    dept_filter    = request.GET.get('department', '')
    date_from      = request.GET.get('date_from', '')
    date_to        = request.GET.get('date_to', '')
    faculty_filter = request.GET.get('faculty', '')

    # ── Determine department scope ────────────────────────────────────────
    if request.user.role == 'HOD':
        user_dept = request.user.department
    else:
        user_dept = None  # Admin = all departments

    # ── Faculty list for dropdown (dept-scoped) ───────────────────────────
    faculty_qs = User.objects.filter(role__in=['Faculty', 'HOD'], is_active=True)
    if user_dept:
        faculty_qs = faculty_qs.filter(department=user_dept)
    elif dept_filter:
        faculty_qs = faculty_qs.filter(department=dept_filter)
    faculty_list = faculty_qs.order_by('full_name')

    # ── Base queryset ─────────────────────────────────────────────────────
    feedbacks = Feedback.objects.select_related('faculty', 'course').all()

    if user_dept:
        feedbacks = feedbacks.filter(course__department=user_dept)
    if dept_filter and not user_dept:
        feedbacks = feedbacks.filter(course__department=dept_filter)
    if date_from:
        feedbacks = feedbacks.filter(submitted_at__date__gte=date_from)
    if date_to:
        feedbacks = feedbacks.filter(submitted_at__date__lte=date_to)
    if faculty_filter:
        feedbacks = feedbacks.filter(faculty_id=faculty_filter)

    total = feedbacks.count()

    # ── Selected faculty info ─────────────────────────────────────────────
    selected_faculty = None
    if faculty_filter:
        try:
            selected_faculty = User.objects.get(id=faculty_filter)
        except User.DoesNotExist:
            pass

    # ── Shared Plotly layout settings ─────────────────────────────────────
    layout_defaults = dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI, sans-serif', color='#374151'),
        margin=dict(l=50, r=30, t=40, b=50),
        hoverlabel=dict(bgcolor='#1e293b', font_color='white', bordercolor='#475569'),
    )

    chart_teacher  = ''
    chart_trend    = ''
    chart_sem      = ''
    chart_dept     = ''
    chart_dist     = ''
    chart_faculty  = ''  # Individual faculty report card

    if total > 0:
        # ── CHART 1: Average Teacher Ratings ──────────────────────────────
        faculty_data = (
            feedbacks
            .exclude(faculty__isnull=True)
            .values('faculty__full_name')
            .annotate(
                avg_teaching=Avg('teaching_rating'),
                avg_content=Avg('content_rating'),
                avg_comm=Avg('communication_rating'),
                count=Count('id'),
            )
            .order_by('-avg_teaching')[:10]
        )
        if faculty_data and not faculty_filter:
            names = [d['faculty__full_name'] for d in faculty_data]
            avgs  = [round(((d['avg_teaching'] or 0) + (d['avg_content'] or 0) + (d['avg_comm'] or 0)) / 3, 2) for d in faculty_data]
            fig1  = go.Figure(go.Bar(
                x=avgs, y=names, orientation='h',
                marker=dict(
                    color=avgs,
                    colorscale=[[0, '#ef4444'], [0.5, '#f59e0b'], [1, '#10b981']],
                    cmin=1, cmax=5,
                ),
                text=[f'{v:.1f}' for v in avgs], textposition='auto',
                hovertemplate='<b>%{y}</b><br>Avg Rating: %{x:.2f}<extra></extra>',
            ))
            fig1.update_layout(
                title='Average Teacher Ratings (Top 10)',
                xaxis=dict(title='Average Rating', range=[0, 5], gridcolor='#f1f5f9'),
                yaxis=dict(autorange='reversed'),
                height=400,
                **layout_defaults,
            )
            chart_teacher = plot(fig1, output_type='div', include_plotlyjs=False)

        # ── CHART (FACULTY-SPECIFIC): Individual Report Card ─────────────
        if faculty_filter and selected_faculty:
            fac_agg = feedbacks.aggregate(
                avg_teaching=Avg('teaching_rating'),
                avg_content=Avg('content_rating'),
                avg_comm=Avg('communication_rating'),
            )
            t_val = round(fac_agg['avg_teaching'] or 0, 2)
            c_val = round(fac_agg['avg_content'] or 0, 2)
            co_val = round(fac_agg['avg_comm'] or 0, 2)

            # Radar chart
            categories = ['Teaching Quality', 'Course Content', 'Communication', 'Teaching Quality']
            values     = [t_val, c_val, co_val, t_val]  # close the polygon

            fig_fac = go.Figure()
            fig_fac.add_trace(go.Scatterpolar(
                r=values, theta=categories,
                fill='toself',
                fillcolor='rgba(99,102,241,0.2)',
                line=dict(color='#6366f1', width=3),
                name=selected_faculty.full_name,
                hovertemplate='%{theta}: %{r:.2f}<extra></extra>',
            ))
            fig_fac.update_layout(
                title=f'Performance Report — {selected_faculty.full_name}',
                polar=dict(
                    radialaxis=dict(range=[0, 5], gridcolor='#e5e7eb', tickfont=dict(size=11)),
                    angularaxis=dict(gridcolor='#e5e7eb'),
                    bgcolor='rgba(0,0,0,0)',
                ),
                height=400,
                **layout_defaults,
            )
            chart_faculty = plot(fig_fac, output_type='div', include_plotlyjs=False)

            # Also generate per-course breakdown for this faculty
            per_course = (
                feedbacks
                .values('course__course_code', 'course__course_name')
                .annotate(
                    count=Count('id'),
                    avg_teaching=Avg('teaching_rating'),
                    avg_content=Avg('content_rating'),
                    avg_comm=Avg('communication_rating'),
                )
                .order_by('course__course_code')
            )
            if per_course:
                codes = [d['course__course_code'] for d in per_course]
                fig_fc = go.Figure()
                fig_fc.add_trace(go.Bar(name='Teaching',      x=codes, y=[round(d['avg_teaching'] or 0, 2) for d in per_course], marker_color='#6366f1'))
                fig_fc.add_trace(go.Bar(name='Content',       x=codes, y=[round(d['avg_content'] or 0, 2) for d in per_course], marker_color='#10b981'))
                fig_fc.add_trace(go.Bar(name='Communication', x=codes, y=[round(d['avg_comm'] or 0, 2) for d in per_course], marker_color='#f59e0b'))
                fig_fc.update_layout(
                    title=f'Course-wise Ratings — {selected_faculty.full_name}',
                    barmode='group',
                    xaxis=dict(title='Course', gridcolor='#f1f5f9'),
                    yaxis=dict(title='Avg Rating', range=[0, 5.5], gridcolor='#f1f5f9'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                    height=380,
                    **layout_defaults,
                )
                chart_teacher = plot(fig_fc, output_type='div', include_plotlyjs=False)

        # ── CHART 2: Course Satisfaction Trends (monthly) ─────────────────
        monthly = (
            feedbacks
            .annotate(month=TruncMonth('submitted_at'))
            .values('month')
            .annotate(
                avg_teaching=Avg('teaching_rating'),
                avg_content=Avg('content_rating'),
                avg_comm=Avg('communication_rating'),
                count=Count('id'),
            )
            .order_by('month')
        )
        if monthly:
            months = [d['month'].strftime('%b %Y') for d in monthly]
            avg_t  = [round(d['avg_teaching'] or 0, 2) for d in monthly]
            avg_c  = [round(d['avg_content']  or 0, 2) for d in monthly]
            avg_co = [round(d['avg_comm']     or 0, 2) for d in monthly]
            fig2   = go.Figure()
            fig2.add_trace(go.Scatter(x=months, y=avg_t,  name='Teaching',      mode='lines+markers', line=dict(color='#6366f1', width=3), marker=dict(size=8)))
            fig2.add_trace(go.Scatter(x=months, y=avg_c,  name='Content',       mode='lines+markers', line=dict(color='#10b981', width=3), marker=dict(size=8)))
            fig2.add_trace(go.Scatter(x=months, y=avg_co, name='Communication', mode='lines+markers', line=dict(color='#f59e0b', width=3), marker=dict(size=8)))
            trend_title = 'Course Satisfaction Trends (Monthly)'
            if selected_faculty:
                trend_title = f'Satisfaction Trends — {selected_faculty.full_name}'
            fig2.update_layout(
                title=trend_title,
                xaxis=dict(title='Month', gridcolor='#f1f5f9'),
                yaxis=dict(title='Avg Rating', range=[0, 5.5], gridcolor='#f1f5f9'),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                height=380,
                **layout_defaults,
            )
            chart_trend = plot(fig2, output_type='div', include_plotlyjs=False)

        # ── CHART 3: Semester-wise Feedback Comparison ───────────────────────────────
        sem_data = (
            feedbacks
            .exclude(course__semester__isnull=True)
            .values('course__semester')
            .annotate(
                count=Count('id'),
                avg_teaching=Avg('teaching_rating'),
                avg_content=Avg('content_rating'),
                avg_comm=Avg('communication_rating')
            )
            .order_by('course__semester')
        )
        if sem_data:
            semesters = [d['course__semester'] for d in sem_data]
            fig3      = go.Figure()
            fig3.add_trace(go.Bar(name='Teaching',      x=semesters, y=[round(d['avg_teaching'] or 0, 2) for d in sem_data], marker_color='#6366f1'))
            fig3.add_trace(go.Bar(name='Content',       x=semesters, y=[round(d['avg_content']  or 0, 2) for d in sem_data], marker_color='#10b981'))
            fig3.add_trace(go.Bar(name='Communication', x=semesters, y=[round(d['avg_comm']     or 0, 2) for d in sem_data], marker_color='#f59e0b'))
            fig3.update_layout(
                title='Semester-wise Ratings Comparison',
                barmode='group',
                xaxis=dict(title='Semester', gridcolor='#f1f5f9'),
                yaxis=dict(title='Avg Rating', range=[0, 5.5], gridcolor='#f1f5f9'),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                height=380,
                **layout_defaults,
            )
            chart_sem = plot(fig3, output_type='div', include_plotlyjs=False)

        # ── CHART 4: Department Comparisons (Admin only) ──────────────────
        if not user_dept and not faculty_filter:
            dept_label_map = dict(User.DEPARTMENT_CHOICES)
            dept_data = (
                feedbacks
                .exclude(course__department__isnull=True)
                .values('course__department')
                .annotate(
                    avg_teaching=Avg('teaching_rating'),
                    avg_content=Avg('content_rating'),
                    avg_comm=Avg('communication_rating'),
                )
                .order_by('course__department')
            )
            if dept_data:
                depts  = [dept_label_map.get(d['course__department'], d['course__department']) for d in dept_data]
                fig4   = go.Figure()
                fig4.add_trace(go.Bar(name='Teaching',      x=depts, y=[round(d['avg_teaching'] or 0, 2) for d in dept_data], marker_color='#6366f1'))
                fig4.add_trace(go.Bar(name='Content',       x=depts, y=[round(d['avg_content']  or 0, 2) for d in dept_data], marker_color='#10b981'))
                fig4.add_trace(go.Bar(name='Communication', x=depts, y=[round(d['avg_comm']     or 0, 2) for d in dept_data], marker_color='#f59e0b'))
                fig4.update_layout(
                    title='Department Comparisons — Avg Ratings',
                    barmode='group',
                    xaxis=dict(title='Department', gridcolor='#f1f5f9'),
                    yaxis=dict(title='Avg Rating', range=[0, 5.5], gridcolor='#f1f5f9'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                    height=400,
                    **layout_defaults,
                )
                chart_dept = plot(fig4, output_type='div', include_plotlyjs=False)

        # ── CHART 5: Rating Distribution (pie) ───────────────────────────
        dist = {star: feedbacks.filter(teaching_rating=star).count() for star in range(1, 6)}
        labels = ['⭐ 1 Star', '⭐⭐ 2 Stars', '⭐⭐⭐ 3 Stars', '⭐⭐⭐⭐ 4 Stars', '⭐⭐⭐⭐⭐ 5 Stars']
        values = [dist[1], dist[2], dist[3], dist[4], dist[5]]
        colors = ['#ef4444', '#f97316', '#f59e0b', '#3b82f6', '#10b981']
        fig5   = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.45,
            marker=dict(colors=colors, line=dict(color='#ffffff', width=2)),
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>',
        ))
        dist_title = 'Rating Distribution (Teaching)'
        if selected_faculty:
            dist_title = f'Rating Distribution — {selected_faculty.full_name}'
        fig5.update_layout(
            title=dist_title,
            height=400,
            **layout_defaults,
        )
        chart_dist = plot(fig5, output_type='div', include_plotlyjs=False)

    # ── Faculty KPIs (when specific faculty selected) ─────────────────────
    faculty_kpis = None
    if selected_faculty and total > 0:
        agg = feedbacks.aggregate(
            avg_t=Avg('teaching_rating'),
            avg_c=Avg('content_rating'),
            avg_co=Avg('communication_rating'),
        )
        faculty_kpis = {
            'total': total,
            'avg_teaching': round(agg['avg_t'] or 0, 1),
            'avg_content': round(agg['avg_c'] or 0, 1),
            'avg_communication': round(agg['avg_co'] or 0, 1),
            'overall': round(((agg['avg_t'] or 0) + (agg['avg_c'] or 0) + (agg['avg_co'] or 0)) / 3, 1),
            'courses_count': feedbacks.values('course').distinct().count(),
        }

    context = {
        'page_title':         'Feedback Analytics',
        'total_feedback':     total,
        'chart_teacher':      chart_teacher,
        'chart_trend':        chart_trend,
        'chart_semester':     chart_sem,
        'chart_dept':         chart_dept,
        'chart_dist':         chart_dist,
        'chart_faculty':      chart_faculty,
        'dept_filter':        dept_filter,
        'date_from':          date_from,
        'date_to':            date_to,
        'faculty_filter':     faculty_filter,
        'faculty_list':       faculty_list,
        'selected_faculty':   selected_faculty,
        'faculty_kpis':       faculty_kpis,
        'department_choices': User.DEPARTMENT_CHOICES,
        'is_hod':             request.user.role == 'HOD',
        'user_dept':          user_dept,
    }
    return render(request, 'users/feedback_analytics.html', context)


# ── APPOINTMENTS ──────────────────────────────────────────────────────────────


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
                    link='/dashboard/appointments/',
                )
            messages.success(request, 'Appointment submitted successfully! You will be notified once approved.')
            return redirect('appointment')
    else:
        form = AppointmentForm(initial={
            'name':        request.user.full_name,
            'roll_number': request.user.student_id,
            'department':  request.user.department,
        })
    return render(request, 'users/appointment.html', {'form': form})


@login_required
def my_appointments(request):
    if request.user.role != 'Student':
        messages.error(request, 'Access denied.')
        return redirect('login')

    from .models import AppointmentUpdate
    appointments = Appointment.objects.filter(
        student=request.user
    ).prefetch_related('updates').order_by('-created_at')

    context = {
        'appointments': appointments,
        'page_title':   'My Appointments',
    }
    return render(request, 'users/my_appointments.html', context)


@login_required
def admin_appointments(request):
    if request.user.role != 'Admin':
        messages.error(request, 'Access denied.')
        return redirect('login')
    appointments  = Appointment.objects.select_related('student').all()
    status_filter = request.GET.get('status', '')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    context = {
        'appointments':  appointments,
        'status_filter': status_filter,
        'total':     Appointment.objects.count(),
        'pending':   Appointment.objects.filter(status='Pending').count(),
        'forwarded': Appointment.objects.filter(status='Forwarded to Committee').count(),
        'scheduled': Appointment.objects.filter(status='Meeting Scheduled').count(),
        'rejected':  Appointment.objects.filter(status='Rejected by Committee').count(),
        'page_title': 'Appointments',
    }
    return render(request, 'users/admin_appointments.html', context)


@login_required
def admin_appointment_detail(request, appointment_id):
    if request.user.role != 'Admin':
        messages.error(request, 'Access denied.')
        return redirect('login')

    from .forms import AdminForwardForm, AdminStudentUpdateForm
    from .models import AppointmentUpdate

    appointment  = get_object_or_404(Appointment, id=appointment_id)
    updates      = AppointmentUpdate.objects.filter(appointment=appointment)
    forward_form = AdminForwardForm(committee_type=appointment.appointment_with)
    student_form = AdminStudentUpdateForm()

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        if action_type == 'forward':
            forward_form = AdminForwardForm(
                request.POST,
                committee_type=appointment.appointment_with
            )
            if forward_form.is_valid():
                member_name = forward_form.cleaned_data['committee_member']
                note        = forward_form.cleaned_data['note']

                appointment.status = 'Forwarded to Committee'
                appointment.save()

                AppointmentUpdate.objects.create(
                    appointment=appointment,
                    updated_by=request.user,
                    message=f'Forwarded to {member_name} ({appointment.appointment_with}). Note: {note}',
                    status='Forwarded to Committee',
                )

                # Notify matching committee members (users with committee_type matching)
                committee_members = User.objects.filter(
                    role='Committee',
                    committee_type=appointment.appointment_with,
                    is_active=True,
                )
                for member in committee_members:
                    Notification.objects.create(
                        recipient=member,
                        title=f'New Appointment Assigned — {appointment.name}',
                        message=f'Admin has forwarded an appointment from {appointment.name} ({appointment.roll_number}). Incident: {appointment.incident_type}. Note: {note}',
                        notification_type='appointment',
                        link=f'/committee/appointment/{appointment.id}/',
                    )

                Notification.objects.create(
                    recipient=appointment.student,
                    title='Appointment Forwarded ✅',
                    message=f'Your appointment has been forwarded to the {appointment.appointment_with}. You will be notified once they respond.',
                    notification_type='appointment',
                    link='/appointment/my/',
                )

                messages.success(request, f'Appointment forwarded to {appointment.appointment_with}.')
                return redirect('admin_appointment_detail', appointment_id=appointment.id)

        elif action_type == 'notify_student':
            student_form = AdminStudentUpdateForm(request.POST)
            if student_form.is_valid():
                msg = student_form.cleaned_data['message']

                AppointmentUpdate.objects.create(
                    appointment=appointment,
                    updated_by=request.user,
                    message=f'[Admin → Student] {msg}',
                    status=appointment.status,
                )

                Notification.objects.create(
                    recipient=appointment.student,
                    title='Appointment Update 📋',
                    message=msg,
                    notification_type='appointment',
                    link='/appointment/my/',
                )

                messages.success(request, 'Student notified successfully.')
                return redirect('admin_appointment_detail', appointment_id=appointment.id)

    context = {
        'appointment':  appointment,
        'updates':      updates,
        'forward_form': forward_form,
        'student_form': student_form,
        'page_title':   'Appointment Detail',
    }
    return render(request, 'users/admin_appointment_detail.html', context)


# ── COMMITTEE ─────────────────────────────────────────────────────────────────

@login_required
def committee_dashboard(request):
    if request.user.role != 'Committee':
        messages.error(request, 'Access denied.')
        return redirect('login')

    from .models import AppointmentUpdate

    appointments = Appointment.objects.filter(
        appointment_with=request.user.committee_type,
        status__in=['Forwarded to Committee', 'Meeting Scheduled', 'Rejected by Committee']
    ).order_by('-created_at')

    context = {
        'appointments': appointments,
        'total':     appointments.count(),
        'pending':   appointments.filter(status='Forwarded to Committee').count(),
        'scheduled': appointments.filter(status='Meeting Scheduled').count(),
        'rejected':  appointments.filter(status='Rejected by Committee').count(),
        'page_title': 'Committee Dashboard',
    }
    return render(request, 'users/committee_dashboard.html', context)


@login_required
def committee_appointment_action(request, appointment_id):
    if request.user.role != 'Committee':
        messages.error(request, 'Access denied.')
        return redirect('login')

    from .forms import CommitteeUpdateForm
    from .models import AppointmentUpdate

    appointment = get_object_or_404(Appointment, id=appointment_id)
    updates     = AppointmentUpdate.objects.filter(appointment=appointment)
    form        = CommitteeUpdateForm()

    if request.method == 'POST':
        form = CommitteeUpdateForm(request.POST)
        if form.is_valid():
            action       = form.cleaned_data['action']
            message      = form.cleaned_data['message']
            meeting_date = form.cleaned_data.get('meeting_date')

            appointment.status = action
            appointment.save()

            AppointmentUpdate.objects.create(
                appointment=appointment,
                updated_by=request.user,
                message=message,
                meeting_date=meeting_date,
                status=action,
            )

            # Notify all admins
            admins = User.objects.filter(role='Admin')
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    title=f'Committee Update — {appointment.name}',
                    message=f'{request.user.full_name} ({request.user.committee_type}) responded to appointment from {appointment.name}. Decision: {action}. Message: {message}',
                    notification_type='appointment',
                    link=f'/dashboard/appointments/{appointment.id}/',
                )

            # Also notify student directly
            Notification.objects.create(
                recipient=appointment.student,
                title=f'Appointment Update — {action}',
                message=f'The {request.user.committee_type} has responded to your appointment. Decision: {action}. {message}',
                notification_type='appointment',
                link='/appointment/my/',
            )

            messages.success(request, 'Response submitted. Admin and student have been notified.')
            return redirect('committee_dashboard')

    context = {
        'appointment': appointment,
        'updates':     updates,
        'form':        form,
        'page_title':  'Review Appointment',
    }
    return render(request, 'users/committee_appointment_action.html', context)


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'users/notifications.html', {
        'notifications': notifications,
        'page_title':    'Notifications',
    })


@login_required
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect('notifications')


# ── TASKS ─────────────────────────────────────────────────────────────────────
@login_required
def task_list(request):
    if request.user.role != 'Student':
        return redirect('home')
    tasks = Task.objects.filter(student=request.user)
    daily = tasks.filter(task_type='Daily')
    weekly = tasks.filter(task_type='Weekly')

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(is_done=True).count()

    return render(request, 'users/task_list.html', {
        'daily': daily,
        'weekly': weekly,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
    })


@login_required
@require_POST
def task_add(request):
    if request.user.role != 'Student':
        return redirect('home')
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    task_type = request.POST.get('task_type', 'Daily')
    priority = request.POST.get('priority', 'Medium')
    due_date = request.POST.get('due_date') or None
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


# ── DAO ───────────────────────────────────────────────────────────────────────

@login_required
def dao_dashboard(request):
    if request.user.role != 'DAO':
        messages.error(request, 'Access denied. DAO only.')
        return redirect('login')

    from django.db.models import Q
    from complaints.models import Complaint, ComplaintUpdate

    dao_handled_ids = ComplaintUpdate.objects.filter(
        updated_by=request.user
    ).values_list('complaint_id', flat=True)

    all_complaints = Complaint.objects.filter(
        Q(assigned_to=request.user) | Q(id__in=dao_handled_ids)
    ).distinct()

    total             = all_complaints.count()
    pending           = all_complaints.filter(status='Pending').count()
    resolved          = all_complaints.filter(status='Resolved').count()
    escalated         = all_complaints.filter(status='Escalated').count()
    assigned_to_staff = all_complaints.filter(status='Under Investigation').count()
    recent            = all_complaints.order_by('-submitted_at')[:5]
    staff_list        = User.objects.filter(role='Staff', is_active=True)

    context = {
        'page_title':          'DAO Dashboard',
        'user':                request.user,
        'assigned_complaints': total,
        'pending_complaints':  pending,
        'resolved_complaints': resolved,
        'escalated_complaints': escalated,
        'assigned_to_staff':   assigned_to_staff,
        'recent_complaints':   recent,
        'staff_list':          staff_list,
    }
    return render(request, 'users/dao_dashboard.html', context)


@login_required
@user_passes_test(lambda u: u.role == 'Admin')
def admin_announcement_list(request):
    from .models import Announcement
    announcements = Announcement.objects.all().order_by('-created_at')
    context = {
        'announcements': announcements,
        'page_title': 'Announcements'
    }
    return render(request, 'users/admin_announcement_list.html', context)


@login_required
@user_passes_test(lambda u: u.role == 'Admin')
def admin_announcement_add(request):
    from .forms import AnnouncementForm
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            messages.success(request, 'Announcement created successfully.')
            return redirect('admin_announcement_list')
    else:
        form = AnnouncementForm()
    context = {
        'form': form,
        'page_title': 'Add Announcement'
    }
    return render(request, 'users/admin_announcement_form.html', context)


@login_required
@user_passes_test(lambda u: u.role == 'Admin')
def admin_announcement_delete(request, announcement_id):
    from .models import Announcement
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if request.method == 'POST':
        title = announcement.title
        announcement.delete()
        messages.success(request, f'Announcement "{title}" deleted.')
        return redirect('admin_announcement_list')
    context = {
        'announcement': announcement,
        'page_title': 'Delete Announcement'
    }
    return render(request, 'users/admin_announcement_delete.html', context)

@login_required
def academic_timeline(request):
    if request.user.role != 'Student':
        messages.error(request, 'Access denied.')
        return redirect('login')

    from complaints.models import Complaint, ComplaintUpdate
    from feedback.models import Feedback
    from users.models import Appointment, Notification

    timeline_items = []

    # Complaints submitted
    for c in Complaint.objects.filter(student=request.user).order_by('-submitted_at'):
        timeline_items.append({
            'type': 'complaint',
            'date': c.submitted_at,
            'title': f'Complaint Filed — {c.tracking_id}',
            'subtitle': c.subject,
            'detail': c.get_complaint_type_display(),
            'status': c.status,
            'link': f'/complaints/detail/{c.id}/',
            'icon': '📢',
            'color': 'red',
        })

    # Complaint updates
    for u in ComplaintUpdate.objects.filter(
        complaint__student=request.user
    ).order_by('-created_at'):
        timeline_items.append({
            'type': 'update',
            'date': u.created_at,
            'title': f'Complaint Update — {u.complaint.tracking_id}',
            'subtitle': u.status_changed_to if u.status_changed_to else 'Comment added',
            'detail': u.comment[:100] if u.comment else '',
            'status': u.status_changed_to or '',
            'link': f'/complaints/detail/{u.complaint.id}/',
            'icon': '🔔',
            'color': 'amber',
        })

    # Feedback submitted
    for f in Feedback.objects.filter(student=request.user).order_by('-submitted_at'):
        timeline_items.append({
            'type': 'feedback',
            'date': f.submitted_at,
            'title': f'Feedback Submitted — {f.course.course_code}',
            'subtitle': f.course.course_name,
            'detail': f'Rating: {f.get_average_rating}/5 ⭐',
            'status': f.status if hasattr(f, 'status') else 'Submitted',
            'link': '',
            'icon': '📝',
            'color': 'blue',
        })

    # Appointments booked
    for a in Appointment.objects.filter(student=request.user).order_by('-created_at'):
        timeline_items.append({
            'type': 'appointment',
            'date': a.created_at,
            'title': f'Appointment Booked',
            'subtitle': f'With: {a.faculty.full_name if hasattr(a, "faculty") and a.faculty else "Faculty"}',
            'detail': a.status,
            'status': a.status,
            'link': '',
            'icon': '📅',
            'color': 'green',
        })

    # Sort all items by date newest first
    timeline_items.sort(key=lambda x: x['date'], reverse=True)

    context = {
        'page_title': 'My Academic Timeline',
        'timeline_items': timeline_items,
        'total': len(timeline_items),
        'complaints_count': Complaint.objects.filter(student=request.user).count(),
        'feedback_count': Feedback.objects.filter(student=request.user).count(),
        'resolved_count': Complaint.objects.filter(student=request.user, status='Resolved').count(),
    }
    return render(request, 'users/academic_timeline.html', context)