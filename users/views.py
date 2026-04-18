
from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render, redirect
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

from .forms import (
    StudentRegistrationForm,
    LoginForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm,
    AdminUserCreateForm,
    AdminUserEditForm,
)
from .models import User
from feedback.models import Feedback
from complaints.models import Complaint




def register_view(request):
    """
    Student registration view.
    GET: Display registration form
    POST: Process registration and create user account
    """
    if request.user.is_authenticated:
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'Account created successfully for {user.full_name}! Please login.'
            )
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentRegistrationForm()

    context = {
        'form': form,
        'page_title': 'Student Registration'
    }
    return render(request, 'users/register.html', context)




def login_view(request):
    """
    Login view for all user types.
    GET: Display login form
    POST: Authenticate user and redirect based on role
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
                    messages.error(request, 'Your account has been deactivated.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()

    context = {
        'form': form,
        'page_title': 'Login'
    }
    return render(request, 'users/login.html', context)


def _redirect_by_role(user):
    """Helper function to redirect user based on role"""
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
    """Logout view"""
    user_name = request.user.get_short_name()
    logout(request)
    messages.success(request, f'Goodbye, {user_name}! You have been logged out.')
    return redirect('login')




def password_reset_request(request):
    """
    Password reset request view.
    GET: Display email form
    POST: Send password reset email
    """
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


                reset_url = request.build_absolute_uri(
                    f'/password-reset/confirm/{uid}/{token}/'
                )

                context = {
                    'user': user,
                    'reset_url': reset_url,
                    'site_name': 'FeedbackFlow',
                }

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

                messages.success(
                    request,
                    'Password reset link has been sent to your email. Please check your inbox.'
                )

            except User.DoesNotExist:
                # Security: same message even if email doesn't exist
                messages.success(
                    request,
                    'If an account exists with this email, a password reset link has been sent.'
                )

            return redirect('login')
    else:
        form = PasswordResetRequestForm()

    context = {
        'form': form,
        'page_title': 'Reset Password'
    }
    return render(request, 'users/password_reset_request.html', context)


def password_reset_confirm(request, uidb64, token):
    """
    Password reset confirmation view.
    Validates token and allows user to set new password.
    """
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

                messages.success(
                    request,
                    'Your password has been reset successfully! Please login with your new password.'
                )
                return redirect('login')
        else:
            form = PasswordResetConfirmForm()

        context = {
            'form': form,
            'validlink': True,
            'page_title': 'Set New Password'
        }
        return render(request, 'users/password_reset_confirm.html', context)

    else:
        messages.error(
            request,
            'Password reset link is invalid or has expired. Please request a new one.'
        )
        return redirect('password_reset_request')


@login_required
def student_dashboard(request):
    """Student dashboard with stats and recent activity"""

    if request.user.role != 'Student':
        messages.error(request, 'Access denied. Students only.')
        return redirect('login')

    from feedback.models import Feedback
    from complaints.models import Complaint

    all_feedback = Feedback.objects.filter(student=request.user)

    total_feedback = all_feedback.count()
    reviewed_count = all_feedback.filter(status__in=['Reviewed', 'Responded']).count()
    pending_feedback = all_feedback.filter(status='Pending').count()


    all_complaints = Complaint.objects.filter(student=request.user)

    total_complaints = all_complaints.count()
    pending_complaints = all_complaints.filter(status='Pending').count()
    resolved_complaints = all_complaints.filter(status='Resolved').count()

    recent_feedback = all_feedback.order_by('-submitted_at')[:3]
    recent_complaints = all_complaints.order_by('-submitted_at')[:2]

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
    }

    return render(request, 'users/student_dashboard.html', context)


@login_required
def faculty_dashboard(request):
    """Faculty dashboard with feedback stats"""

    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('login')


    from feedback.models import Feedback, Course
    from django.db.models import Avg

    all_feedback = Feedback.objects.filter(course__faculty=request.user)
    courses = Course.objects.filter(faculty=request.user, is_active=True)

    total_feedback = all_feedback.count()
    pending_response = all_feedback.filter(status='Pending').count()


    avg_ratings = all_feedback.aggregate(
        avg_all=Avg('teaching_rating')
    )
    average_rating = round(avg_ratings['avg_all'] or 0, 1)


    from datetime import timedelta
    from django.utils import timezone
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
    """HOD dashboard with complaints and department stats"""

    if request.user.role != 'HOD':
        messages.error(request, 'Access denied. HOD only.')
        return redirect('login')

    from complaints.models import Complaint
    from feedback.models import Feedback


    all_complaints = Complaint.objects.filter(assigned_to=request.user)

    total_complaints = all_complaints.count()
    pending_complaints = all_complaints.filter(status='Pending').count()
    resolved_complaints = all_complaints.filter(status='Resolved').count()
    escalated_complaints = all_complaints.filter(status='Escalated').count()


    from users.models import User
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
    """Staff dashboard with facility complaints"""

    if request.user.role != 'Staff':
        messages.error(request, 'Access denied. Staff only.')
        return redirect('login')


    from complaints.models import Complaint


    all_complaints = Complaint.objects.filter(assigned_to=request.user)

    assigned_complaints = all_complaints.count()
    pending_complaints = all_complaints.filter(status='Pending').count()
    in_progress_complaints = all_complaints.filter(status='Under Investigation').count()
    resolved_complaints = all_complaints.filter(status='Resolved').count()

    # Recent complaints
    recent_complaints = all_complaints.order_by('-submitted_at')[:5]

    context = {
        'page_title': 'Staff Dashboard',
        'user': request.user,


        'assigned_complaints': assigned_complaints,
        'pending_complaints': pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
        'avg_resolution_time': 0,  # TODO: Calculate this


        'recent_complaints': recent_complaints,
        'has_complaints': assigned_complaints > 0,
    }

    return render(request, 'users/staff_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """Admin dashboard with system-wide stats"""

    if request.user.role != 'Admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('login')

    from django.db.models import Count
    from feedback.models import Feedback
    from complaints.models import Complaint

    # Real user statistics
    user_stats = User.objects.values('role').annotate(count=Count('id'))
    role_counts = {stat['role']: stat['count'] for stat in user_stats}


    total_feedback = Feedback.objects.count()


    total_complaints = Complaint.objects.count()
    pending_complaints = Complaint.objects.filter(status='Pending').count()

    context = {
        'page_title': 'Admin Dashboard',
        'user': request.user,


        'total_users': User.objects.count(),
        'student_count': role_counts.get('Student', 0),
        'faculty_count': role_counts.get('Faculty', 0),
        'hod_count': role_counts.get('HOD', 0),
        'staff_count': role_counts.get('Staff', 0),
        'admin_count': role_counts.get('Admin', 0),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),


        'department_stats': User.objects.filter(department__isnull=False) \
            .values('department').annotate(count=Count('id')),


        'total_feedback': total_feedback,
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,


        'recent_users': User.objects.order_by('-created_at')[:5],
    }

    return render(request, 'users/admin_dashboard.html', context)



@login_required
def admin_user_list(request):
   """Admin can view and search all users."""
   if request.user.role != 'Admin':
       return redirect('login')


   users = User.objects.all().order_by('-created_at')


   search = request.GET.get('search', '')
   role_filter = request.GET.get('role', '')
   dept_filter = request.GET.get('department', '')


   if search:
       users = users.filter(
           full_name__icontains=search
       ) | users.filter(
           email__icontains=search
       )


   if role_filter:
       users = users.filter(role=role_filter)


   if dept_filter:
       users = users.filter(department=dept_filter)


   context = {
       'users': users,
       'search': search,
       'role_filter': role_filter,
       'dept_filter': dept_filter,
       'roles': User.ROLE_CHOICES,
       'departments': User.DEPARTMENT_CHOICES,
   }
   return render(request, 'users/admin_user_list.html', context)




@login_required
def admin_user_create(request):
   """Admin can create a new user of any role."""
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


   return render(request, 'users/admin_user_form.html', {
       'form': form,
       'action': 'Create'
   })




@login_required
def admin_user_edit(request, user_id):
   """Admin can edit an existing user."""
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


   return render(request, 'users/admin_user_form.html', {
       'form': form,
       'action': 'Edit',
       'target_user': target_user
   })




@login_required
def admin_user_delete(request, user_id):
   """Admin can delete a user (with confirmation)."""
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


   return render(request, 'users/admin_user_delete.html', {
       'target_user': target_user
   })




@login_required
def admin_user_toggle_active(request, user_id):
   """Admin can activate or deactivate a user."""
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

