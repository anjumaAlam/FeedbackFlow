

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=200)
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

    def get_primary_faculty(self):
        assignment = self.assignments.filter(is_primary=True).first()
        if not assignment:
            assignment = self.assignments.first()
        return assignment.faculty if assignment else None

    def get_faculty_names(self):
        return ', '.join(a.faculty.full_name for a in self.assignments.select_related('faculty'))


class CourseAssignment(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_assignments',
        limit_choices_to={'role__in': ['Faculty', 'HOD']}
    )
    SECTION_CHOICES = (
        ('A', 'Section A'),
        ('B', 'Section B'),
        ('C', 'Section C'),
        ('D', 'Section D'),
    )
    class_section = models.CharField(max_length=1, choices=SECTION_CHOICES, null=True, blank=True, help_text='Assign faculty for a specific section')
    is_primary = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['course', 'class_section']
        ordering = ['-is_primary', 'faculty__full_name']
        verbose_name = 'Course Assignment'
        verbose_name_plural = 'Course Assignments'

    def __str__(self):
        label = ' (Primary)' if self.is_primary else ''
        section = f' [Section {self.class_section}]' if self.class_section else ''
        return f"{self.faculty.full_name} → {self.course.course_code}{section}{label}"


class Feedback(models.Model):
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

    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedback_received',
        limit_choices_to={'role__in': ['Faculty', 'HOD']}
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

    SECTION_CHOICES = (
        ('A', 'Section A'),
        ('B', 'Section B'),
        ('C', 'Section C'),
        ('D', 'Section D'),
    )

    class_section = models.CharField(
        max_length=1,
        choices=SECTION_CHOICES,
        blank=True,
        null=True
    )

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
        unique_together = ['student', 'course']

    def __str__(self):
        return f"Feedback by {self.student.email} for {self.course.course_code}"

    def get_average_rating(self):
        return round((self.teaching_rating + self.content_rating + self.communication_rating) / 3, 1)


class FeedbackResponse(models.Model):
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
class CourseRegistration(models.Model):
    student      = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.CASCADE,
                        related_name='course_registrations'
                    )
    course       = models.ForeignKey(
                        Course,
                        on_delete=models.CASCADE,
                        related_name='registrations'
                    )
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    registered_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-registered_at']

    def __str__(self):
        status = "Confirmed" if self.is_confirmed else "Pending"
        return f"{self.student.full_name} → {self.course.course_code} [{status}]"