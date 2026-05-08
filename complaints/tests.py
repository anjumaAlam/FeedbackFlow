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

    def test_facility_complaint_assigned_to_staff(self):
        """Facility complaint auto-assigns to a Staff user"""
        staff = make_user('staff@uap-bd.edu', 'Staff')
        complaint = self._make_complaint(complaint_type='Facility')
        self.assertEqual(complaint.assigned_to, staff)

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