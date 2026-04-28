# complaints/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone


class Complaint(models.Model):
    """
    Model to store student complaints.
    Auto-routes to appropriate handler based on complaint type.
    """

    COMPLAINT_TYPE_CHOICES = (
        ('Faculty', 'Complaint about Faculty'),
        ('HOD', 'Complaint about HOD'),
        ('Staff', 'Complaint about Staff'),
        ('Facility', 'Facility Issue'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending Review'),
        ('Under Investigation', 'Under Investigation'),
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
        null=True,
        blank=True,
        related_name='complaints_against',
        limit_choices_to={'role__in': ['Faculty', 'HOD', 'Staff']}
    )
    location = models.CharField(max_length=200, blank=True, null=True, help_text='For facility issues')


    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')


    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='complaints_assigned'
    )


    is_anonymous = models.BooleanField(default=False)


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
        # Generate tracking ID if not exists
        if not self.tracking_id:
            import random
            import string
            self.tracking_id = 'CMP' + ''.join(random.choices(string.digits, k=6))


        if not self.assigned_to:
            self.auto_assign_handler()

        super().save(*args, **kwargs)

    def auto_assign_handler(self):
        """Auto-assign complaint to appropriate handler"""
        from users.models import User

        if self.complaint_type == 'Faculty':
            try:
                if self.faculty_concerned:
                    hod = User.objects.filter(role='HOD', department=self.faculty_concerned.department).first()
                else:
                    hod = User.objects.filter(role='HOD', department=self.student.department).first()
                if hod:
                    self.assigned_to = hod
                else:
                    self.assigned_to = User.objects.filter(role='Admin').first()
            except Exception:
                self.assigned_to = User.objects.filter(role='Admin').first()

        elif self.complaint_type == 'HOD':
            self.assigned_to = User.objects.filter(role='Admin').first()

        elif self.complaint_type == 'Staff':
            self.assigned_to = User.objects.filter(role='Admin').first()

        elif self.complaint_type == 'Facility':
            self.assigned_to = User.objects.filter(role='Staff').first()


class ComplaintUpdate(models.Model):
    """
    Model to store updates/comments on complaints.
    """
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='updates'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    comment = models.TextField()
    status_changed_to = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Complaint Update'
        verbose_name_plural = 'Complaint Updates'

    def __str__(self):
        return f"Update on {self.complaint.tracking_id} by {self.updated_by.full_name}"