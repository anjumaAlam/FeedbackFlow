# complaints/forms.py

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import Complaint, ComplaintUpdate, ComplaintInvestigation, InvestigationFinding

User = get_user_model()


class ComplaintSubmissionForm(forms.ModelForm):
    """Form for students to submit complaints."""
    class Meta:
        model = Complaint
        fields = ['complaint_type', 'subject', 'description', 'faculty_concerned', 'location', 'is_anonymous']
        widgets = {
            'complaint_type': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief title of the issue or advice'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Provide detailed information about your complaint, advice, or suggestion...'}),
            'faculty_concerned': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Room 301, Library, Cafeteria'}),
            'is_anonymous': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'complaint_type': 'Category',
            'subject': 'Subject',
            'description': 'Detailed Description',
            'faculty_concerned': 'Faculty/Staff Member (if applicable)',
            'location': 'Location (for facility issues)',
            'is_anonymous': 'Submit Anonymously'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from users.models import User

        role_map = {
            'Faculty': ['Faculty'],
            'HOD': ['HOD'],
            'Staff': ['Staff'],
            'Facility': ['Staff'],
            'Suggestion': [],
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
            self.fields['faculty_concerned'].queryset = (
                User.objects.filter(role__in=roles, is_active=True).order_by('full_name')
            )
        else:
            self.fields['faculty_concerned'].queryset = User.objects.none()

        self.fields['faculty_concerned'].required = False


class ComplaintUpdateForm(forms.ModelForm):
    """Form for HOD/Staff/Admin to update complaints."""
    class Meta:
        model = ComplaintUpdate
        fields = ['comment', 'status_changed_to']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Add your comment or update...'}),
            'status_changed_to': forms.Select(attrs={'class': 'form-select'})
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
        self.fields['comment'].required = False


class AssignInvestigationForm(forms.ModelForm):
    """HOD uses this form to assign one or more faculty investigators."""

    investigators = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'investigation-checkbox'}),
        label='Assign Investigators',
        help_text='Select one or more faculty members to investigate this complaint.',
        required=True,
    )

    class Meta:
        model = ComplaintInvestigation
        fields = ['investigators', 'description', 'due_date']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': (
                    'Describe the scope of investigation, specific concerns to address, '
                    'and any relevant context from the complaint...'
                ),
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
        }
        labels = {
            'description': 'Investigation Brief / Forwarded Details',
            'due_date': 'Expected Completion Date (optional)',
        }

    def __init__(self, *args, complaint=None, hod_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if hod_user:
            self.fields['investigators'].queryset = (
                User.objects.filter(
                    role__in=['Faculty', 'HOD'],
                    department=hod_user.department,
                    is_active=True,
                )
                .exclude(pk=hod_user.pk)
                .order_by('full_name')
            )
        if complaint and not self.instance.pk:
            self.fields['description'].initial = (
                f"Complaint Reference: {complaint.tracking_id}\n"
                f"Type: {complaint.get_complaint_type_display()}\n"
                f"Subject: {complaint.subject}\n\n"
                f"Complaint Details:\n{complaint.description}\n\n"
                f"--- Please investigate the above matter and report your findings. ---"
            )


class InvestigationFindingsForm(forms.ModelForm):
    """Faculty investigator submits findings and verdict back to HOD."""
    class Meta:
        model = InvestigationFinding
        fields = ['verdict', 'findings']
        widgets = {
            'verdict': forms.Select(attrs={'class': 'form-select'}),
            'findings': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 7,
                'placeholder': 'Describe your investigation findings in detail — evidence gathered, people spoken to, observations made...'
            }),
        }
        labels = {
            'verdict': 'Your Verdict',
            'findings': 'Detailed Findings',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['verdict'].choices = [('', '-- Select Verdict --')] + list(InvestigationFinding.VERDICT_CHOICES)


class HODFinalActionForm(forms.Form):
    """HOD takes final action after reviewing investigator findings."""

    ACTION_CHOICES = (
        ('Resolve', '✅  Resolve — Mark complaint as resolved'),
        ('Escalate', '⬆️  Escalate — Send to Admin for further action'),
        ('More Investigation', '🔍  Request More Investigation — Send back to investigators'),
    )

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Final Action'
    )

    note = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Write a note to the student explaining the outcome or next steps...'
        }),
        label='Note to Student',
    )

    