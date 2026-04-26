

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

        self.fields['course'].queryset = Course.objects.filter(is_active=True)

        if user:
            already_submitted = Feedback.objects.filter(student=user).values_list('course_id', flat=True)
            self.fields['course'].queryset = self.fields['course'].queryset.exclude(id__in=already_submitted)

        # All Faculty/HOD users — JS filters by course, clean() validates assignment
        self.fields['faculty'].queryset = User.objects.filter(role__in=['Faculty', 'HOD'])
        self.fields['faculty'].empty_label = '— Select a course first —'

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        faculty = cleaned_data.get('faculty')
        teaching = cleaned_data.get('teaching_rating')
        content = cleaned_data.get('content_rating')
        communication = cleaned_data.get('communication_rating')

        if course and faculty:
            if not CourseAssignment.objects.filter(course=course, faculty=faculty).exists():
                self.add_error('faculty', 'Selected faculty is not assigned to this course.')

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
