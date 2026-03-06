# users/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import re
from .models import User

DEPARTMENT_CHOICES = [
    ('', 'Select Department'),  # Empty option
    ('DBA', 'Department of Business Administration (DBA)'),
    ('CSE', 'Department of Computer Science and Engineering (CSE)'),
    ('CE', 'Department of Civil Engineering (CE)'),
    ('EEE', 'Department of Electrical and Electronic Engineering (EEE)'),
    ('Pharmacy', 'Department of Pharmacy'),
    ('Law', 'Department of Law and Human Rights'),
    ('English', 'Department of English'),
    ('Architecture', 'Department of Architecture'),
]
class StudentRegistrationForm(forms.ModelForm):
    """
    Registration form for students.
    Auto-assigns 'Student' role.
    Includes password strength validation and UAP email domain check.
    """



    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        help_text='Password must be at least 8 characters with uppercase, lowercase, number, and special character.'
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = User
        fields = ['full_name', 'student_id', 'email', 'department']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full name'
            }),
            'student_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 23101164'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.name@uap-bd.edu'
            }),
            'department': forms.Select(
                choices=DEPARTMENT_CHOICES,
                attrs={
                    'class': 'form-select'
                }
            ),
        }
        help_texts = {
            'email': 'Must be a valid UAP email (@uap-bd.edu)',
            'student_id': 'Your university student ID number',
        }

    def clean_email(self):
        """
        Validate email:
        1. Must be from UAP domain (@uap-bd.edu)
        2. Must be unique
        """
        email = self.cleaned_data.get('email')

        # Check UAP domain
        if not email.endswith('@uap-bd.edu'):
            raise forms.ValidationError(
                'Email must be from UAP domain (@uap-bd.edu). '
                'Example: yourname@uap-bd.edu'
            )

        # Check uniqueness
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')

        return email

    def clean_student_id(self):
        """
        Validate student ID:
        1. Must be unique
        2. Should be numeric
        """
        student_id = self.cleaned_data.get('student_id')

        # Check if it's numeric
        if not student_id.isdigit():
            raise forms.ValidationError('Student ID must contain only numbers.')

        # Check uniqueness
        if User.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError('This student ID is already registered.')

        return student_id

    def clean_department(self):
        """Validate department is selected"""
        department = self.cleaned_data.get('department')
        if not department:
            raise forms.ValidationError('Please select a department.')
        return department

    def clean_password(self):
        """
        Validate password strength:
        - At least 8 characters
        - Contains uppercase letter
        - Contains lowercase letter
        - Contains number
        - Contains special character
        """
        password = self.cleaned_data.get('password')

        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')

        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('Password must contain at least one uppercase letter.')

        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('Password must contain at least one lowercase letter.')

        if not re.search(r'\d', password):
            raise forms.ValidationError('Password must contain at least one number.')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise forms.ValidationError('Password must contain at least one special character (!@#$%^&* etc.).')

        return password

    def clean(self):
        """Validate passwords match."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError('Passwords do not match.')

        return cleaned_data

    def save(self, commit=True):
        """Save user with hashed password and Student role."""
        user = super().save(commit=False)
        user.role = 'Student'  # Auto-assign Student role
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """
    Login form for all users.
    """
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your UAP email',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        })
    )


class PasswordResetRequestForm(forms.Form):
    """
    Form for requesting password reset.
    User enters their email to receive reset link.
    """
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your UAP email',
            'autocomplete': 'email'
        }),
        help_text='Enter the email address associated with your account.'
    )

    def clean_email(self):
        """Validate that email is from UAP domain"""
        email = self.cleaned_data.get('email')

        # Check if email is from UAP domain
        if not email.endswith('@uap-bd.edu'):
            raise forms.ValidationError(
                'Please enter a valid UAP email address (@uap-bd.edu)'
            )

        return email


class PasswordResetConfirmForm(forms.Form):
    """
    Form for setting new password after clicking reset link.
    """
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        help_text='Password must be at least 8 characters with uppercase, lowercase, number, and special character.'
    )
    confirm_password = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )

    def clean_new_password(self):
        """
        Validate password strength (same rules as registration)
        """
        password = self.cleaned_data.get('new_password')

        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')

        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('Password must contain at least one uppercase letter.')

        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('Password must contain at least one lowercase letter.')

        if not re.search(r'\d', password):
            raise forms.ValidationError('Password must contain at least one number.')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise forms.ValidationError('Password must contain at least one special character.')

        return password

    def clean(self):
        """Validate passwords match"""
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError('Passwords do not match.')

        return cleaned_data