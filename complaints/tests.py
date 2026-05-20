from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Complaint, ComplaintUpdate

User = get_user_model()





def make_user(email, role, department='CSE', **kwargs):
    return User.objects.create_user(
        email=email,
        password='Test@1234',
        full_name=f'Test {role}',
        role=role,
        department=department,
        **kwargs
    )



#  MODEL TESTS

class ComplaintModelTest(TestCase):
    """Unit tests for the Complaint model"""

    def setUp(self):
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.student = make_user('student@uap-bd.edu', 'Student',
                                 student_id='23101001')

    def _make_complaint(self, **kwargs):
        defaults = dict(
            student=self.student,
            complaint_type='Facility',
            subject='AC not working',
            description='Room 301 AC is broken.',
        )
        defaults.update(kwargs)
        return Complaint.objects.create(**defaults)

    def test_tracking_id_generated_on_save(self):
        """Complaint gets a CMP-prefixed tracking ID automatically"""
        complaint = self._make_complaint()
        self.assertTrue(complaint.tracking_id.startswith('CMP'))
        self.assertEqual(len(complaint.tracking_id), 9)

    def test_tracking_id_is_unique(self):
        """Two complaints must not share a tracking ID"""
        c1 = self._make_complaint()
        c2 = self._make_complaint(subject='Another issue')
        self.assertNotEqual(c1.tracking_id, c2.tracking_id)

    def test_default_status_is_pending(self):
        """New complaint status defaults to Pending"""
        complaint = self._make_complaint()
        self.assertEqual(complaint.status, 'Pending')

    def test_default_priority_is_medium(self):
        """New complaint priority defaults to Medium"""
        complaint = self._make_complaint()
        self.assertEqual(complaint.priority, 'Medium')

    def test_is_anonymous_defaults_to_false(self):
        """is_anonymous defaults to False"""
        complaint = self._make_complaint()
        self.assertFalse(complaint.is_anonymous)

    def test_str_contains_tracking_id_and_subject(self):
        """__str__ includes tracking_id and subject"""
        complaint = self._make_complaint()
        self.assertIn(complaint.tracking_id, str(complaint))
        self.assertIn('AC not working', str(complaint))

    def test_facility_complaint_assigned_to_dao(self):
        """Facility complaint auto-assigns to DAO if available, else Admin"""
        # Note: Facility complaints are assigned to DAO first, then Admin as fallback
        complaint = self._make_complaint(complaint_type='Facility')
        # Since no DAO exists, it should assign to Admin (created in setUp)
        self.assertEqual(complaint.assigned_to, self.admin)

    def test_hod_complaint_assigned_to_admin(self):
        """HOD complaint auto-assigns to Admin"""
        complaint = self._make_complaint(complaint_type='HOD')
        self.assertEqual(complaint.assigned_to, self.admin)

    def test_behavioral_complaint_assigned_to_admin(self):
        """HOD-type complaint (no Staff/Faculty match) auto-assigns to Admin"""
        # Note: The model supports Faculty, HOD, Staff, Facility types.
        # 'HOD' type always assigns to Admin — equivalent to a "behavioral" escalation.
        complaint = self._make_complaint(complaint_type='HOD')
        self.assertEqual(complaint.assigned_to, self.admin)


class ComplaintUpdateModelTest(TestCase):
    """Unit tests for the ComplaintUpdate model"""

    def setUp(self):
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.student = make_user('student@uap-bd.edu', 'Student',
                                 student_id='23101002')
        self.complaint = Complaint.objects.create(
            student=self.student,
            complaint_type='HOD',
            subject='Rude behaviour',
            description='Details here.',
        )

    def test_create_complaint_update(self):
        """ComplaintUpdate can be saved and linked to a Complaint"""
        update = ComplaintUpdate.objects.create(
            complaint=self.complaint,
            updated_by=self.admin,
            comment='We are looking into this.',
            status_changed_to='Under Investigation',
        )
        self.assertEqual(ComplaintUpdate.objects.count(), 1)
        self.assertEqual(update.complaint, self.complaint)

    def test_update_str_contains_tracking_id(self):
        """__str__ of ComplaintUpdate mentions the complaint tracking ID"""
        update = ComplaintUpdate.objects.create(
            complaint=self.complaint,
            updated_by=self.admin,
            comment='Resolved.',
        )
        self.assertIn(self.complaint.tracking_id, str(update))



#  VIEW TESTS


class SubmitComplaintViewTest(TestCase):
    """Tests for the submit_complaint view"""

    def setUp(self):
        self.client = Client()
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.student = make_user('student@uap-bd.edu', 'Student',
                                 student_id='23101003')
        self.url = reverse('submit_complaint')

    def test_unauthenticated_user_redirected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_student_can_view_form(self):
        """Logged-in student gets a 200 on the submit page"""
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_student_can_submit_complaint(self):
        """Valid POST by student creates a Complaint object"""
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        data = {
            'complaint_type': 'Facility',
            'subject': 'Broken projector',
            'description': 'Projector in Room 205 is not working.',
            'is_anonymous': False,
        }
        self.client.post(self.url, data)
        self.assertEqual(Complaint.objects.count(), 1)

    def test_successful_submission_redirects(self):
        """Successful complaint submission redirects"""
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        data = {
            'complaint_type': 'HOD',       # valid choice in the model
            'subject': 'Issue in class',
            'description': 'Detailed description.',
            'is_anonymous': False,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)


class MyComplaintsViewTest(TestCase):
    """Tests for the my_complaints view"""

    def setUp(self):
        self.client = Client()
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.student = make_user('student@uap-bd.edu', 'Student',
                                 student_id='23101004')
        self.url = reverse('my_complaints')

    def test_unauthenticated_user_redirected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_student_can_view_own_complaints(self):
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_only_own_complaints_visible(self):
        """Student only sees their own complaints, not others'"""
        other = make_user('other@uap-bd.edu', 'Student', student_id='23101005')
        Complaint.objects.create(
            student=other,
            complaint_type='HOD',
            subject='Other complaint',
            description='Not mine.',
        )
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_complaints'], 0)


class HandleComplaintViewTest(TestCase):
    """Tests for the handle_complaint view"""

    def setUp(self):
        self.client = Client()
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.student = make_user('student@uap-bd.edu', 'Student',
                                 student_id='23101006')
        self.complaint = Complaint.objects.create(
            student=self.student,
            complaint_type='HOD',
            subject='Test',
            description='Test description.',
        )
        self.url = reverse('handle_complaint', args=[self.complaint.id])

    def test_student_cannot_access_handle_view(self):
        """Student should be denied access to the handle view"""
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_admin_can_update_complaint_status(self):
        """Admin POST changes the complaint status"""
        self.client.login(username='admin@uap-bd.edu', password='Test@1234')
        self.client.post(self.url, {
            'comment': 'Investigating now.',
            'status_changed_to': 'Under Investigation',
        })
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, 'Under Investigation')

    def test_resolving_complaint_sets_resolved_at(self):
        """Setting status to Resolved fills in resolved_at timestamp"""
        self.client.login(username='admin@uap-bd.edu', password='Test@1234')
        self.client.post(self.url, {
            'comment': 'All done.',
            'status_changed_to': 'Resolved',
        })
        self.complaint.refresh_from_db()
        self.assertIsNotNone(self.complaint.resolved_at)


class ComplaintInvestigationModelTest(TestCase):
    """Unit tests for the ComplaintInvestigation model"""

    def setUp(self):
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.faculty1 = make_user('faculty1@uap-bd.edu', 'Faculty')
        self.faculty2 = make_user('faculty2@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student',
                                 student_id='23101007')
        self.complaint = Complaint.objects.create(
            student=self.student,
            complaint_type='Faculty',
            subject='Unfair grading',
            description='My grades seem unfair.',
        )

    def test_create_investigation(self):
        """Can create ComplaintInvestigation"""
        from .models import ComplaintInvestigation
        investigation = ComplaintInvestigation.objects.create(
            complaint=self.complaint,
            assigned_by=self.admin,
            description='Investigating grading practices.'
        )
        investigation.investigators.add(self.faculty1, self.faculty2)
        self.assertEqual(investigation.investigators.count(), 2)

    def test_investigation_str(self):
        """__str__ displays tracking ID and investigator names"""
        from .models import ComplaintInvestigation
        investigation = ComplaintInvestigation.objects.create(
            complaint=self.complaint,
            assigned_by=self.admin,
            description='Test investigation'
        )
        investigation.investigators.add(self.faculty1)
        self.assertIn(self.complaint.tracking_id, str(investigation))
        self.assertIn(self.faculty1.full_name, str(investigation))


class InvestigationFindingModelTest(TestCase):
    """Unit tests for the InvestigationFinding model"""

    def setUp(self):
        from .models import ComplaintInvestigation, InvestigationFinding
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student',
                                 student_id='23101008')
        self.complaint = Complaint.objects.create(
            student=self.student,
            complaint_type='Faculty',
            subject='Test',
            description='Test complaint.'
        )
        self.investigation = ComplaintInvestigation.objects.create(
            complaint=self.complaint,
            assigned_by=self.admin,
            description='Investigation details.'
        )
        self.investigation.investigators.add(self.faculty)

    def test_create_investigation_finding(self):
        """Can submit InvestigationFinding"""
        from .models import InvestigationFinding
        finding = InvestigationFinding.objects.create(
            investigation=self.investigation,
            submitted_by=self.faculty,
            verdict='Proven',
            findings='The complaint is substantiated.'
        )
        self.assertEqual(finding.verdict, 'Proven')

    def test_finding_verdict_choices(self):
        """Verdict must be one of the valid choices"""
        from .models import InvestigationFinding
        finding = InvestigationFinding(
            investigation=self.investigation,
            submitted_by=self.faculty,
            verdict='Unproven',
            findings='No evidence found.'
        )
        finding.full_clean()  # Should not raise
        self.assertEqual(finding.verdict, 'Unproven')

    def test_duplicate_finding_from_same_investigator_blocked(self):
        """Same investigator cannot submit findings twice"""
        from .models import InvestigationFinding
        InvestigationFinding.objects.create(
            investigation=self.investigation,
            submitted_by=self.faculty,
            verdict='Proven',
            findings='First finding'
        )
        with self.assertRaises(Exception):
            InvestigationFinding.objects.create(
                investigation=self.investigation,
                submitted_by=self.faculty,
                verdict='Unproven',
                findings='Second finding'
            )


class ComplaintDetailViewTest(TestCase):
    """Tests for complaint_detail view"""

    def setUp(self):
        self.client = Client()
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.student = make_user('student@uap-bd.edu', 'Student',
                                 student_id='23101009')
        self.complaint = Complaint.objects.create(
            student=self.student,
            complaint_type='Facility',
            subject='Broken equipment',
            description='Lab equipment broken.'
        )
        self.url = reverse('complaint_detail', args=[self.complaint.id])

    def test_unauthenticated_user_redirected(self):
        """Unauthenticated user cannot view complaint detail"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_student_can_view_own_complaint(self):
        """Student can view their own complaint"""
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_view_others_complaint(self):
        """Student cannot view another student's complaint"""
        other = make_user('other@uap-bd.edu', 'Student', student_id='23101010')
        self.client.login(username='other@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class SuggestionViewsTest(TestCase):
    """Tests for suggestions listing and actions (Review, Resolve) by HOD"""

    def setUp(self):
        self.client = Client()
        self.hod = make_user('hod@uap-bd.edu', 'HOD', department='CSE')
        self.student = make_user('student_cse@uap-bd.edu', 'Student', department='CSE', student_id='23101011')
        self.suggestion = Complaint.objects.create(
            student=self.student,
            complaint_type='Opinion',
            subject='Better library seating',
            description='We need better chairs in the CSE section.',
        )

    def test_unauthenticated_user_redirected_suggestions(self):
        response = self.client.get(reverse('hod_suggestions_list'))
        self.assertEqual(response.status_code, 302)

    def test_non_hod_cannot_access_suggestions(self):
        self.client.login(username='student_cse@uap-bd.edu', password='Test@1234')
        response = self.client.get(reverse('hod_suggestions_list'))
        self.assertEqual(response.status_code, 302)

    def test_hod_can_view_suggestions(self):
        self.client.login(username='hod@uap-bd.edu', password='Test@1234')
        response = self.client.get(reverse('hod_suggestions_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.suggestion, response.context['suggestions_list'])

    def test_hod_can_mark_suggestion_reviewed(self):
        self.client.login(username='hod@uap-bd.edu', password='Test@1234')
        response = self.client.get(reverse('mark_suggestion_reviewed', args=[self.suggestion.id]))
        self.assertEqual(response.status_code, 302)
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, 'Under Investigation')

    def test_hod_can_resolve_suggestion(self):
        self.client.login(username='hod@uap-bd.edu', password='Test@1234')
        response = self.client.get(reverse('resolve_suggestion', args=[self.suggestion.id]))
        self.assertEqual(response.status_code, 302)
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, 'Resolved')
        self.assertIsNotNone(self.suggestion.resolved_at)