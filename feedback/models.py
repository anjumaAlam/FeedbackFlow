

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Course(models.Model):
    """
    Model to store course information.
    Each course is taught by a faculty member.
    """
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=200)
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses_taught',
        limit_choices_to={'role__in': ['Faculty', 'HOD']}
    )
    department = models.CharField(max_length=100)
    semester = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['course_code']
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"


class Feedback(models.Model):
    """
    Model to store student feedback for courses.
    Students rate courses on teaching, content, and communication.
    """
    STATUS_CHOICES = (
        ('Pending', 'Pending Review'),
        ('Reviewed', 'Reviewed'),
        ('Responded', 'Responded'),
    )


    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedback_submitted'
    )


    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='feedback_received'
    )


    teaching_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Rate teaching quality (1-5 stars)'
    )
    content_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Rate course content (1-5 stars)'
    )
    communication_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Rate communication (1-5 stars)'
    )


    comments = models.TextField(blank=True, null=True)


    is_anonymous = models.BooleanField(default=False)


    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )


    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'
        # Prevent duplicate feedback for same course by same student
        unique_together = ['student', 'course']

    def __str__(self):
        return f"Feedback by {self.student.email} for {self.course.course_code}"

    def get_average_rating(self):
        """Calculate average rating across all categories"""
        return round((self.teaching_rating + self.content_rating + self.communication_rating) / 3, 1)


class FeedbackResponse(models.Model):
    """
    Model to store faculty responses to student feedback.
    """
    feedback = models.OneToOneField(
        Feedback,
        on_delete=models.CASCADE,
        related_name='response'
    )
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedback_responses'
    )
    response_text = models.TextField()
    responded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-responded_at']
        verbose_name = 'Feedback Response'
        verbose_name_plural = 'Feedback Responses'

    def __str__(self):
        return f"Response to {self.feedback.id} by {self.faculty.full_name}"