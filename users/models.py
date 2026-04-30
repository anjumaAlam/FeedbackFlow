from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier
    instead of username.
    """

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError('Email address is required')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('role', 'Admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('full_name', 'Administrator')
        extra_fields.setdefault('department', 'Administration')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for FeedbackFlow system.
    Uses email instead of username for authentication.
    """

    ROLE_CHOICES = (
        ('Student', 'Student'),
        ('Faculty', 'Faculty'),
        ('HOD', 'Head of Department'),
        ('Staff', 'Staff'),
        ('Admin', 'Administrator'),
    )

    DEPARTMENT_CHOICES = (
        ('DBA', 'Department of Business Administration'),
        ('CSE', 'Department of Computer Science and Engineering'),
        ('CE', 'Department of Civil Engineering'),
        ('EEE', 'Department of Electrical and Electronic Engineering'),
        ('Pharmacy', 'Department of Pharmacy'),
        ('Law', 'Department of Law and Human Rights'),
        ('English', 'Department of English'),
        ('Architecture', 'Department of Architecture'),
    )

    email = models.EmailField(unique=True, max_length=255)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES, null=True, blank=True)
    student_id = models.CharField(max_length=50, unique=True, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def get_short_name(self):
        """Return the short name for the user."""
        return self.full_name.split()[0] if self.full_name else self.email

    def get_department_display_full(self):
        """Get full department name"""
        return dict(self.DEPARTMENT_CHOICES).get(self.department, self.department)


# ↓ Appointment is OUTSIDE the User class — at the same level
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    PLACE_CHOICES = [
        ('Faculty Office', 'Faculty Office'),
        ('HOD Office', 'HOD Office'),
        ('Meeting Room A', 'Meeting Room A'),
        ('Meeting Room B', 'Meeting Room B'),
        ('Online (Zoom/Meet)', 'Online (Zoom/Meet)'),
    ]

    DEPARTMENT_CHOICES = (
        ('DBA', 'Department of Business Administration (DBA)'),
        ('CSE', 'Department of Computer Science and Engineering (CSE)'),
        ('CE', 'Department of Civil Engineering (CE)'),
        ('EEE', 'Department of Electrical and Electronic Engineering (EEE)'),
        ('Pharmacy', 'Department of Pharmacy'),
        ('Law', 'Department of Law and Human Rights'),
        ('English', 'Department of English'),
        ('Architecture', 'Department of Architecture'),
    )

    student        = models.ForeignKey('User', on_delete=models.CASCADE, related_name='appointments')
    name           = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20)
    department     = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES)
    description    = models.TextField()
    place          = models.CharField(max_length=100, choices=PLACE_CHOICES)
    preferred_time = models.DateTimeField()
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'

    def __str__(self):
        return f"{self.name} ({self.student_id}) - {self.status}"