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
        ('Student',   'Student'),
        ('Faculty',   'Faculty'),
        ('HOD',       'Head of Department'),
        ('Staff',     'Staff'),
        ('DAO',       'Dean of Administration Office'),
        ('Admin',     'Administrator'),
        ('Committee', 'Committee Member'),
    )

    DEPARTMENT_CHOICES = (
        ('DBA',          'Department of Business Administration'),
        ('CSE',          'Department of Computer Science and Engineering'),
        ('CE',           'Department of Civil Engineering'),
        ('EEE',          'Department of Electrical and Electronic Engineering'),
        ('Pharmacy',     'Department of Pharmacy'),
        ('Law',          'Department of Law and Human Rights'),
        ('English',      'Department of English'),
        ('Architecture', 'Department of Architecture'),
    )

    COMMITTEE_TYPE_CHOICES = (
        ('Harassment Committee', 'Harassment Committee'),
        ('Proctorial Committee', 'Proctorial Committee'),
    )

    email          = models.EmailField(unique=True, max_length=255)
    full_name      = models.CharField(max_length=150)
    role           = models.CharField(max_length=20, choices=ROLE_CHOICES)
    department     = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES, null=True, blank=True)
    student_id     = models.CharField(max_length=50, unique=True, null=True, blank=True)
    committee_type = models.CharField(max_length=50, choices=COMMITTEE_TYPE_CHOICES, null=True, blank=True)
    is_active      = models.BooleanField(default=True)
    is_staff       = models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']
    objects = UserManager()

    class Meta:
        verbose_name        = 'User'
        verbose_name_plural = 'Users'
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email

    def get_department_display_full(self):
        return dict(self.DEPARTMENT_CHOICES).get(self.department, self.department)


# ─────────────────────────────────────────────────────────────
# APPOINTMENT
# ─────────────────────────────────────────────────────────────

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending',                'Pending'),
        ('Forwarded to Committee', 'Forwarded to Committee'),
        ('Meeting Scheduled',      'Meeting Scheduled'),
        ('Rejected by Committee',  'Rejected by Committee'),
        ('Resolved Informally',    'Resolved Informally'),    # NEW
        ('Needs Formal Action',    'Needs Formal Action'),    # NEW
        ('Closed',                 'Closed'),
    ]

    OUTCOME_CHOICES = [
        ('Pending',             'Pending — No outcome yet'),
        ('Resolved Informally', 'Resolved Informally — Case closed'),
        ('Needs Formal Action', 'Needs Formal Action — Student should file complaint'),
    ]

    DEPARTMENT_CHOICES = (
        ('DBA',          'Department of Business Administration (DBA)'),
        ('CSE',          'Department of Computer Science and Engineering (CSE)'),
        ('CE',           'Department of Civil Engineering (CE)'),
        ('EEE',          'Department of Electrical and Electronic Engineering (EEE)'),
        ('Pharmacy',     'Department of Pharmacy'),
        ('Law',          'Department of Law and Human Rights'),
        ('English',      'Department of English'),
        ('Architecture', 'Department of Architecture'),
    )

    COMMITTEE_CHOICES = [
        ('Harassment Committee', 'Harassment Committee'),
        ('Proctorial Committee', 'Proctorial Committee'),
    ]

    INCIDENT_TYPE_CHOICES = [
        ('Harassment',      'Harassment'),
        ('Bullying',        'Bullying'),
        ('Discrimination',  'Discrimination'),
        ('Faculty Misconduct', 'Faculty Misconduct'),
        ('Mental Pressure', 'Mental Pressure'),
        ('Abuse',           'Abuse'),
        ('Other',           'Other'),
    ]

    student          = models.ForeignKey('User', on_delete=models.CASCADE, related_name='appointments')
    name             = models.CharField(max_length=100)
    roll_number      = models.CharField(max_length=20)
    appointment_with = models.CharField(max_length=50, choices=COMMITTEE_CHOICES, default='Harassment Committee')
    department       = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES)
    incident_type    = models.CharField(max_length=50, choices=INCIDENT_TYPE_CHOICES, default='Other')
    description      = models.TextField()

    # Meeting location (general field)
    meeting_location = models.CharField(max_length=200, blank=True, null=True,
        help_text='e.g. Room 204, Admin Block / Google Meet link')

    # Outcome set by committee after the discussion session
    outcome          = models.CharField(max_length=30, choices=OUTCOME_CHOICES, default='Pending')

    # If outcome = Needs Formal Action, store the pre-filled complaint reference
    converted_to_complaint = models.ForeignKey(
        'complaints.Complaint',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='from_appointment'
    )

    TYPE_CHOICES = [
        ('Appointment', 'Appointment'),
        ('Direct Complaint', 'Direct Complaint'),
    ]
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='Appointment'
    )



    status     = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Appointment'
        verbose_name_plural = 'Appointments'

    def __str__(self):
        return f"{self.name} ({self.roll_number}) - {self.status}"

    @property
    def can_convert_to_complaint(self):
        return self.outcome == 'Needs Formal Action' and self.converted_to_complaint is None


# ─────────────────────────────────────────────────────────────
# APPOINTMENT UPDATE
# ─────────────────────────────────────────────────────────────

class AppointmentUpdate(models.Model):
    STATUS_CHOICES = [
        ('Pending',                'Pending'),
        ('Forwarded to Committee', 'Forwarded to Committee'),
        ('Meeting Scheduled',      'Meeting Scheduled'),
        ('Rejected by Committee',  'Rejected by Committee'),
        ('Resolved Informally',    'Resolved Informally'),
        ('Needs Formal Action',    'Needs Formal Action'),
        ('Closed',                 'Closed'),
    ]

    appointment  = models.ForeignKey('Appointment', on_delete=models.CASCADE, related_name='updates')
    updated_by   = models.ForeignKey('User', on_delete=models.CASCADE, related_name='appointment_updates')
    message      = models.TextField()
    meeting_date = models.DateTimeField(null=True, blank=True)
    status       = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.appointment} — {self.updated_by.full_name}"


# ─────────────────────────────────────────────────────────────
# APPOINTMENT NOTE  (CONFIDENTIAL — committee + admin only)
# ─────────────────────────────────────────────────────────────

class AppointmentNote(models.Model):
    """
    Private notes added by committee member during/after the discussion.
    Student NEVER sees these. Only committee member and admin can view.
    Examples: 'Student appeared distressed', 'Needs follow-up', etc.
    """
    appointment = models.ForeignKey('Appointment', on_delete=models.CASCADE, related_name='notes')
    added_by    = models.ForeignKey('User', on_delete=models.CASCADE, related_name='appointment_notes')
    note        = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note by {self.added_by.full_name} on {self.appointment}"


# ─────────────────────────────────────────────────────────────
# NOTIFICATION
# ─────────────────────────────────────────────────────────────

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('complaint',    'Complaint'),
        ('appointment',  'Appointment'),
        ('update',       'Complaint Update'),
        ('feedback',     'Feedback'),
        ('announcement', 'Announcement'),
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


# ─────────────────────────────────────────────────────────────
# TASK
# ─────────────────────────────────────────────────────────────

class Task(models.Model):
    PRIORITY_CHOICES = (
        ('Low',    'Low'),
        ('Medium', 'Medium'),
        ('High',   'High'),
    )
    TYPE_CHOICES = (
        ('Daily',  'Daily'),
        ('Weekly', 'Weekly'),
    )

    student     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    task_type   = models.CharField(max_length=10, choices=TYPE_CHOICES, default='Daily')
    priority    = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    is_done     = models.BooleanField(default=False)
    due_date    = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_done', '-priority', 'created_at']

    def __str__(self):
        return f"{self.student.full_name} — {self.title}"


# ─────────────────────────────────────────────────────────────
# ANNOUNCEMENT
# ─────────────────────────────────────────────────────────────

class Announcement(models.Model):
    PRIORITY_CHOICES = (
        ('Low',      'Low'),
        ('Normal',   'Normal'),
        ('High',     'High'),
        ('Critical', 'Critical'),
    )

    title        = models.CharField(max_length=200)
    content      = models.TextField()
    priority     = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Normal')
    target_roles = models.CharField(max_length=200, blank=True, default='',
        help_text='Comma-separated roles (e.g. Student,Faculty). Leave blank for all.')
    created_by   = models.ForeignKey('User', on_delete=models.CASCADE, related_name='announcements_created')
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    expires_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Announcement'
        verbose_name_plural = 'Announcements'

    def __str__(self):
        return f"{self.title} ({self.get_priority_display()})"

    @property
    def is_expired(self):
        from django.utils import timezone
        return bool(self.expires_at and timezone.now() > self.expires_at)

    def is_visible_to(self, user):
        if self.is_expired or not self.is_active:
            return False
        if not self.target_roles:
            return True
        allowed = [r.strip() for r in self.target_roles.split(',')]
        return user.role in allowed