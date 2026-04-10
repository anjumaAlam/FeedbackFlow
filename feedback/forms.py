

from django import forms
from .models import Feedback, FeedbackResponse, Course


class FeedbackSubmissionForm(forms.ModelForm):
    """
    Form for students to submit course feedback.
    """

    class Meta:
        model = Feedback
        fields = ['course', 'teaching_rating', 'content_rating', 'communication_rating', 'comments', 'is_anonymous']
        widgets = {
            'course': forms.Select(attrs={
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

    def clean(self):
        cleaned_data = super().clean()
        teaching = cleaned_data.get('teaching_rating')
        content = cleaned_data.get('content_rating')
        communication = cleaned_data.get('communication_rating')


        for rating, name in [(teaching, 'Teaching'), (content, 'Content'), (communication, 'Communication')]:
            if rating and (rating < 1 or rating > 5):
                raise forms.ValidationError(f'{name} rating must be between 1 and 5.')

        return cleaned_data


class FeedbackResponseForm(forms.ModelForm):
    """
    Form for faculty to respond to student feedback.
    """

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