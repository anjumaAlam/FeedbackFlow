# complaints/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone


class Complaint(models.Model):
    COMPLAINT_TYPE_CHOICES = (
        ('Faculty', 'Complaint about Faculty'),
        ('HOD', 'Complaint about HOD'),
        ('Staff', 'Complaint about Staff'),
        ('Facility', 'Facility Issue'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending Review'),
        ('Under Investigation', 'Under Investigation'),
        ('Findings Submitted', 'Findings Submitted'),       # NEW
        ('Resolved', 'Resolved'),
        ('Escalated', 'Escalated to Higher Authority'),
    )

    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='complaints_submitted'
    )
    complaint_type = models.CharField(max_length=20, choices=COMPLAINT_TYPE_CHOICES)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    faculty_concerned = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='complaints_against',
        limit_choices_to={'role__in': ['Faculty', 'HOD', 'Staff']}
    )
    location = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='complaints_assigned'
    )
    is_anonymous = models.BooleanField(default=False)

    # HOD's final note sent to student when closing the complaint
    final_action_note = models.TextField(blank=True, null=True)          # NEW

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    tracking_id = models.CharField(max_length=20, unique=True, editable=False)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Complaint'
        verbose_name_plural = 'Complaints'

    def __str__(self):
        return f"{self.tracking_id} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            import random, string
            self.tracking_id = 'CMP' + ''.join(random.choices(string.digits, k=6))
        if not self.assigned_to:
            self.auto_assign_handler()
        super().save(*args, **kwargs)

    def auto_assign_handler(self):
        from users.models import User
        if self.complaint_type == 'Faculty':
            if self.faculty_concerned:
                hod = User.objects.filter(role='HOD', department=self.faculty_concerned.department).first()
            else:
                hod = User.objects.filter(role='HOD', department=self.student.department).first()
            self.assigned_to = hod or User.objects.filter(role='Admin').first()
        elif self.complaint_type == 'HOD':
            self.assigned_to = User.objects.filter(role='Admin').first()
        elif self.complaint_type == 'Staff':
            staff = User.objects.filter(role='Staff', department=self.student.department).first()
            self.assigned_to = staff or User.objects.filter(role='Admin').first()
        elif self.complaint_type == 'Facility':
            dao = User.objects.filter(role='DAO').first()
            self.assigned_to = dao if dao else User.objects.filter(role='Admin').first()

class ComplaintUpdate(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='updates')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField(blank=True, null=True)
    status_changed_to = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Update on {self.complaint.tracking_id} by {self.updated_by.full_name}"


class ComplaintInvestigation(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name='investigation')
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='investigations_assigned_by'
    )
    investigators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='investigations_assigned_to',
        limit_choices_to={'role__in': ['Faculty', 'HOD']},
    )
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        names = ', '.join(i.full_name for i in self.investigators.all())
        return f"Investigation for {self.complaint.tracking_id} → {names}"

    @property
    def all_findings_submitted(self):
        """True when every assigned investigator has submitted their findings."""
        investigator_ids = set(self.investigators.values_list('id', flat=True))
        submitted_ids = set(self.findings.values_list('submitted_by_id', flat=True))
        return investigator_ids == submitted_ids and len(investigator_ids) > 0


class InvestigationFinding(models.Model):
    """Faculty investigator submits findings back to HOD."""
    VERDICT_CHOICES = (
        ('Proven', 'Complaint is Proven'),
        ('Unproven', 'Complaint is Unproven'),
        ('Needs More Info', 'Needs More Info'),
    )

    investigation = models.ForeignKey(
        ComplaintInvestigation, on_delete=models.CASCADE, related_name='findings'
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='investigation_findings'
    )
    verdict = models.CharField(max_length=30, choices=VERDICT_CHOICES)
    findings = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ('investigation', 'submitted_by')

    def __str__(self):
        return f"Finding by {self.submitted_by.full_name} on {self.investigation.complaint.tracking_id}"