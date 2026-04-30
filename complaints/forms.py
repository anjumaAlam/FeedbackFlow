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
        from users.models import User

        # Keep queryset aligned with selected complaint type so POSTed IDs validate.
        role_map = {
            'Faculty': ['Faculty'],
            'HOD': ['HOD'],
            'Staff': ['Staff'],
            'Facility': ['Staff'],
        }

        selected_type = None
        if self.is_bound:
            selected_type = self.data.get('complaint_type')
        elif self.instance and getattr(self.instance, 'complaint_type', None):
            selected_type = self.instance.complaint_type
        else:
            selected_type = self.initial.get('complaint_type')

        roles = role_map.get(selected_type, [])
        if roles:
            self.fields['faculty_concerned'].queryset = User.objects.filter(
                role__in=roles,
                is_active=True,
            ).order_by('full_name')
        else:
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