from django import forms
from .models import Complaint, ComplaintUpdate


class ComplaintSubmissionForm(forms.ModelForm):
    """
    Form for students to submit complaints.
    """
    class Meta:
        model = Complaint
        fields = ['complaint_type', 'subject', 'description', 'faculty_concerned', 'location', 'is_anonymous']
        widgets = {
            'complaint_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of the issue'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Provide detailed information about your complaint...'
            }),
            'faculty_concerned': forms.Select(attrs={
                'class': 'form-select'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Room 301, Library, Cafeteria'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'complaint_type': 'Type of Complaint',
            'subject': 'Subject',
            'description': 'Detailed Description',
            'faculty_concerned': 'Faculty/Staff Member (if applicable)',
            'location': 'Location (for facility issues)',
            'is_anonymous': 'Submit Anonymously'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show faculty, HOD, and staff in the dropdown
        from users.models import User
        # Start with an empty queryset; frontend JS will populate based on complaint type
        self.fields['faculty_concerned'].queryset = User.objects.none()
        self.fields['faculty_concerned'].required = False


class ComplaintUpdateForm(forms.ModelForm):
    """
    Form for HOD/Staff/Admin to update complaints.
    """
    class Meta:
        model = ComplaintUpdate
        fields = ['comment', 'status_changed_to']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Add your comment or update...'
            }),
            'status_changed_to': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'comment': 'Comment/Update',
            'status_changed_to': 'Change Status To'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        status_choices = [('', 'No Status Change')] + list(Complaint.STATUS_CHOICES)
        self.fields['status_changed_to'].choices = status_choices
        self.fields['status_changed_to'].widget.choices = status_choices
        self.fields['status_changed_to'].required = False