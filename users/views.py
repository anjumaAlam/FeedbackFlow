# users/views.py

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

from .forms import (
    StudentRegistrationForm,
    LoginForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm
)
from .models import User


# ============================================
# REGISTRATION
# ============================================

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


# ============================================
# LOGIN
# ============================================

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


# ============================================
# LOGOUT
# ============================================

@login_required
def logout_view(request):
    """Logout view"""
    user_name = request.user.get_short_name()
    logout(request)
    messages.success(request, f'Goodbye, {user_name}! You have been logged out.')
    return redirect('login')


# ============================================
# PASSWORD RESET
# ============================================

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

                # Generate token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                # Build reset URL
                reset_url = request.build_absolute_uri(
                    f'/password-reset/confirm/{uid}/{token}/'
                )

                # Email context
                context = {
                    'user': user,
                    'reset_url': reset_url,
                    'site_name': 'FeedbackFlow',
                }

                # Send email
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


# ============================================
# TEMPORARY DASHBOARDS (to be built later)
# ============================================

@login_required
def student_dashboard(request):
    """Temporary student dashboard"""
    if request.user.role != 'Student':
        messages.error(request, 'Access denied. Students only.')
        return redirect('login')

    context = {
        'page_title': 'Student Dashboard',
        'user': request.user
    }
    return render(request, 'users/student_dashboard.html', context)


@login_required
def faculty_dashboard(request):
    """Temporary faculty dashboard"""
    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('login')

    context = {
        'page_title': 'Faculty Dashboard',
        'user': request.user
    }
    return render(request, 'users/faculty_dashboard.html', context)


@login_required
def hod_dashboard(request):
    """Temporary HOD dashboard"""
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied. HOD only.')
        return redirect('login')

    context = {
        'page_title': 'HOD Dashboard',
        'user': request.user
    }
    return render(request, 'users/hod_dashboard.html', context)


@login_required
def staff_dashboard(request):
    """Temporary staff dashboard"""
    if request.user.role != 'Staff':
        messages.error(request, 'Access denied. Staff only.')
        return redirect('login')

    context = {
        'page_title': 'Staff Dashboard',
        'user': request.user
    }
    return render(request, 'users/staff_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """Temporary admin dashboard"""
    if request.user.role != 'Admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('login')

    context = {
        'page_title': 'Admin Dashboard',
        'user': request.user
    }
    return render(request, 'users/admin_dashboard.html', context)