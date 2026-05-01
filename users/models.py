from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'Admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('full_name', 'Administrator')
        extra_fields.setdefault('department', 'Administration')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
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
        return self.full_name.split()[0] if self.full_name else self.email

    def get_department_display_full(self):
        return dict(self.DEPARTMENT_CHOICES).get(self.department, self.department)


# ↓ OUTSIDE User class
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
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

    COMMITTEE_CHOICES = [
        ('Harassment Committee', 'Harassment Committee'),
        ('Proctorial Committee', 'Proctorial Committee'),
    ]

    INCIDENT_TYPE_CHOICES = [
        ('Harassment', 'Harassment'),
        ('Discrimination', 'Discrimination'),
        ('Abuse', 'Abuse'),
        ('Other', 'Other'),
    ]

    student          = models.ForeignKey('User', on_delete=models.CASCADE, related_name='appointments')
    name             = models.CharField(max_length=100)
    roll_number      = models.CharField(max_length=20)
    appointment_with = models.CharField(max_length=50, choices=COMMITTEE_CHOICES, default='Harassment Committee')
    department       = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES)
    incident_type    = models.CharField(max_length=50, choices=INCIDENT_TYPE_CHOICES, default='Other')
    description      = models.TextField()
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'

    def __str__(self):
        return f"{self.name} ({self.roll_number}) - {self.status}"


# ↓ OUTSIDE Appointment class
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('complaint', 'Complaint'),
        ('appointment', 'Appointment'),
        ('update', 'Complaint Update'),
    ]

    recipient         = models.ForeignKey('User', on_delete=models.CASCADE, related_name='notifications')
    title             = models.CharField(max_length=200)
    message           = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    link              = models.CharField(max_length=200, blank=True, null=True)
    is_read           = models.BooleanField(default=False)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.full_name} - {self.title}"