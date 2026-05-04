

from django import forms
from django.contrib.auth import get_user_model
from .models import Feedback, FeedbackResponse, Course, CourseAssignment

User = get_user_model()


class FeedbackSubmissionForm(forms.ModelForm):

    class Meta:
        model = Feedback
        fields = ['course', 'faculty', 'class_section', 'teaching_rating', 'content_rating', 'communication_rating', 'comments', 'is_anonymous']
        widgets = {
            'course': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_course'
            }),
            'faculty': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_faculty'
            }),
            'class_section': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'teaching_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'type': 'number',
                'placeholder': 'Rate 1-5'
            }),
            'content_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'type': 'number',
                'placeholder': 'Rate 1-5'
            }),
            'communication_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'type': 'number',
                'placeholder': 'Rate 1-5'
            }),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your thoughts about this course... (optional)'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'course': 'Select Course',
            'faculty': 'Select Faculty',
            'class_section': 'Class Section',
            'teaching_rating': 'Teaching Quality',
            'content_rating': 'Course Content',
            'communication_rating': 'Communication',
            'comments': 'Additional Comments',
            'is_anonymous': 'Submit Anonymously'
        }
        help_texts = {
            'teaching_rating': 'How would you rate the teaching quality? (1=Poor, 5=Excellent)',
            'content_rating': 'How would you rate the course content? (1=Poor, 5=Excellent)',
            'communication_rating': 'How would you rate faculty communication? (1=Poor, 5=Excellent)',
            'is_anonymous': 'Your identity will be hidden from the faculty if checked'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Base queryset — only active courses
        qs = Course.objects.filter(is_active=True)

        if user and getattr(user, 'department', None):
            # Filter to student's confirmed registered courses only
            from .models import CourseRegistration
            confirmed_ids = CourseRegistration.objects.filter(
                student=user,
                is_confirmed=True,
                course__is_active=True
            ).values_list('course_id', flat=True)

            if confirmed_ids:
                qs = qs.filter(id__in=confirmed_ids)
            else:
                # Student has no confirmed registrations — show nothing
                qs = Course.objects.none()

        # Exclude courses already submitted feedback for
        if user:
            already_submitted = Feedback.objects.filter(
                student=user
            ).values_list('course_id', flat=True)
            qs = qs.exclude(id__in=already_submitted)

        self.fields['course'].queryset = qs

        if not qs.exists():
            self.fields['course'].empty_label = '— No registered courses found. Please register first. —'

        # Faculty
        self.fields['faculty'].queryset = User.objects.filter(role__in=['Faculty', 'HOD'])
        self.fields['faculty'].empty_label = '— Select a course and section first —'

        course_id = self.data.get('course') or self.initial.get('course')
        section = self.data.get('class_section') or self.initial.get('class_section')
        if course_id and section:
            assigned_faculty_ids = CourseAssignment.objects.filter(
                course_id=course_id,
                class_section=section,
            ).values_list('faculty_id', flat=True)
            if assigned_faculty_ids:
                self.fields['faculty'].queryset = User.objects.filter(
                    id__in=assigned_faculty_ids
                )

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        section = cleaned_data.get('class_section')
        faculty = cleaned_data.get('faculty')
        teaching = cleaned_data.get('teaching_rating')
        content = cleaned_data.get('content_rating')
        communication = cleaned_data.get('communication_rating')

        if course and section and faculty:
            if not CourseAssignment.objects.filter(course=course, class_section=section, faculty=faculty).exists():
                self.add_error('faculty', 'Selected faculty is not assigned to this course and section.')

        if course and section and not faculty:
            self.add_error('faculty', 'Select the faculty assigned to this course and section.')

        for rating, name in [(teaching, 'Teaching'), (content, 'Content'), (communication, 'Communication')]:
            if rating and (rating < 1 or rating > 5):
                raise forms.ValidationError(f'{name} rating must be between 1 and 5.')

        return cleaned_data


class FeedbackResponseForm(forms.ModelForm):

    class Meta:
        model = FeedbackResponse
        fields = ['response_text']
        widgets = {
            'response_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Write your response to this feedback...'
            })
        }
        labels = {
            'response_text': 'Your Response'
        }


class CourseAssignmentForm(forms.ModelForm):
    class Meta:
        model = CourseAssignment
        fields = ['course', 'class_section', 'faculty', 'is_primary']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'class_section': forms.Select(attrs={'class': 'form-select'}),
            'faculty': forms.Select(attrs={'class': 'form-select'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show faculty users with Faculty/HOD roles
        self.fields['faculty'].queryset = User.objects.filter(role__in=['Faculty', 'HOD'], is_active=True)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_code', 'course_name', 'department', 'semester', 'is_active']
        widgets = {
            'course_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CSE101'}),
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Course name'}),
            'department': forms.Select(choices=User.DEPARTMENT_CHOICES, attrs={'class': 'form-select'}),
            'semester': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Spring 2026'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
