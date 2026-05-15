from django import forms
from django.core.exceptions import ValidationError
import re
from .models import User, Announcement

DEPARTMENT_CHOICES = [
    ('', 'Select Department'),
    ('DBA', 'Department of Business Administration (DBA)'),
    ('CSE', 'Department of Computer Science and Engineering (CSE)'),
    ('CE', 'Department of Civil Engineering (CE)'),
    ('EEE', 'Department of Electrical and Electronic Engineering (EEE)'),
    ('Pharmacy', 'Department of Pharmacy'),
    ('Law', 'Department of Law and Human Rights'),
    ('English', 'Department of English'),
    ('Architecture', 'Department of Architecture'),
    ('Administration', 'Administration'),
]


class StudentRegistrationForm(forms.ModelForm):
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
                attrs={'class': 'form-select'}
            ),
        }
        help_texts = {
            'email': 'Must be a valid UAP email (@uap-bd.edu)',
            'student_id': 'Your university student ID number',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email.endswith('@uap-bd.edu'):
            raise ValidationError('Only UAP email addresses (@uap-bd.edu) are allowed.')
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email is already registered.')
        return email

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id', '').strip()
        if not student_id:
            raise ValidationError('Student ID is required.')
        if not student_id.isdigit():
            raise ValidationError('Student ID must contain only numbers.')
        if User.objects.filter(student_id=student_id, role='Student').exists():
            raise ValidationError('This student ID is already registered.')
        return student_id

    def clean_department(self):
        department = self.cleaned_data.get('department')
        if not department:
            raise ValidationError('Please select a department.')
        return department

    def clean_password(self):
        password = self.cleaned_data.get('password')
        return validate_strong_password(password)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'Student'
        user.email = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
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
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email.endswith('@uap-bd.edu'):
            raise ValidationError('Please enter a valid UAP email address (@uap-bd.edu)')
        return email


class PasswordResetConfirmForm(forms.Form):
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
        password = self.cleaned_data.get('new_password')
        return validate_strong_password(password)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Passwords do not match.')
        return cleaned_data


class AdminUserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
    )

    class Meta:
        model = User
        fields = ['full_name', 'email', 'role', 'department', 'student_id', 'committee_type']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@uap-bd.edu'
            }),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(
                choices=DEPARTMENT_CHOICES,
                attrs={'class': 'form-select'}
            ),
            'student_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Student ID (students only)'
            }),
            'committee_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email is already registered.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        return validate_strong_password(password)

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        student_id = (cleaned_data.get('student_id') or '').strip()
        if role == 'Student':
            if not student_id:
                raise ValidationError('Student ID is required for student accounts.')
            if not student_id.isdigit():
                raise ValidationError('Student ID must contain only numbers.')
            if User.objects.filter(student_id=student_id, role='Student').exists():
                raise ValidationError('This student ID is already registered.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        if user.role == 'Admin':
            user.is_staff = True
        else:
            user.is_staff = False
        if commit:
            user.save()
        return user


class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'email', 'role', 'department', 'student_id', 'committee_type', 'is_active']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(
                choices=DEPARTMENT_CHOICES,
                attrs={'class': 'form-select'}
            ),
            'student_id': forms.TextInput(attrs={'class': 'form-control'}),
            'committee_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        student_id = (cleaned_data.get('student_id') or '').strip()
        if role == 'Student':
            if not student_id:
                raise ValidationError('Student ID is required for student accounts.')
            if not student_id.isdigit():
                raise ValidationError('Student ID must contain only numbers.')
            exists = User.objects.filter(
                student_id=student_id,
                role='Student'
            ).exclude(pk=self.instance.pk).exists()
            if exists:
                raise ValidationError('This student ID is already registered.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if user.role == 'Admin':
            user.is_staff = True
        elif not user.is_superuser:
            user.is_staff = False
        if commit:
            user.save()
        return user


def validate_strong_password(password):
    if not password:
        raise ValidationError('Password is required.')
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter.')
    if not re.search(r'\d', password):
        raise ValidationError('Password must contain at least one number.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('Password must contain at least one special character.')
    return password


class AppointmentForm(forms.Form):
    name = forms.CharField(
        label='Full Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your full name'
        })
    )
    roll_number = forms.CharField(
        label='Student ID',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 23101164'
        })
    )
    appointment_with = forms.ChoiceField(
        label='Book Appointment With',
        choices=[
            ('', '---------'),
            ('Harassment Committee', 'Harassment Committee'),
            ('Proctorial Committee', 'Proctorial Committee'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ChoiceField(
        label='Department',
        choices=[
            ('', '---------'),
            ('DBA', 'Department of Business Administration (DBA)'),
            ('CSE', 'Department of Computer Science and Engineering (CSE)'),
            ('CE', 'Department of Civil Engineering (CE)'),
            ('EEE', 'Department of Electrical and Electronic Engineering (EEE)'),
            ('Pharmacy', 'Department of Pharmacy'),
            ('Law', 'Department of Law and Human Rights'),
            ('English', 'Department of English'),
            ('Architecture', 'Department of Architecture'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    incident_type = forms.ChoiceField(
        label='Type of Incident',
        choices=[
            ('', '---------'),
            ('Harassment', 'Harassment'),
            ('Discrimination', 'Discrimination'),
            ('Abuse', 'Abuse'),
            ('Other', 'Other'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    description = forms.CharField(
        label='Description of Incident',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describe the incident in detail...'
        })
    )


class CommitteeUpdateForm(forms.Form):
    action = forms.ChoiceField(
        label='Action',
        choices=[
            ('Meeting Scheduled', 'Schedule a Meeting Date'),
            ('Rejected by Committee', 'Reject this Request'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    message = forms.CharField(
        label='Message / Reason',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Provide details about your decision...'
        })
    )
    meeting_date = forms.DateTimeField(
        label='Meeting Date & Time (if scheduling)',
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        meeting_date = cleaned_data.get('meeting_date')
        if action == 'Meeting Scheduled' and not meeting_date:
            raise ValidationError('Please provide a meeting date and time.')
        return cleaned_data


class AdminForwardForm(forms.Form):
    committee_member = forms.ModelChoiceField(
        queryset=None,
        label='Select Committee Member',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    note = forms.CharField(
        label='Note to Committee',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add context or instructions for the committee...'
        })
    )

    def __init__(self, *args, committee_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        if committee_type:
            self.fields['committee_member'].queryset = User.objects.filter(
                role='Committee',
                committee_type=committee_type,
                is_active=True
            )
        else:
            self.fields['committee_member'].queryset = User.objects.filter(
                role='Committee',
                is_active=True
            )


class AdminStudentUpdateForm(forms.Form):
    message = forms.CharField(
        label='Message to Student',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Write the update message for the student...'
        })
    )


class AnnouncementForm(forms.ModelForm):
    TARGET_ROLE_CHOICES = [
        ('', 'All (Everyone)'),
        ('Student', 'Student'),
        ('Faculty', 'Faculty'),
        ('HOD', 'Head of Department'),
        ('Staff', 'Staff'),
        ('DAO', 'Dean of Administration Office'),
        ('Admin', 'Administrator'),
        ('Committee', 'Committee Member'),
    ]

    target_roles = forms.ChoiceField(
        choices=TARGET_ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Select the specific role to target, or leave as All.'
    )

    class Meta:
        model = Announcement
        fields = ['title', 'content', 'priority', 'target_roles', 'is_active', 'expires_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Announcement Title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write announcement content here...'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expires_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }