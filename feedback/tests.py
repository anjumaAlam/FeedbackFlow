from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from feedback.models import Course, Feedback, FeedbackResponse

User = get_user_model()




def make_user(email, role, department='CSE', **kwargs):
    return User.objects.create_user(
        email=email, password='Test@1234',
        full_name=f'Test {role}', role=role,
        department=department, **kwargs
    )

def make_course(faculty, code='CSE101'):
    return Course.objects.create(
        course_code=code, course_name='Intro to CS',
        faculty=faculty, department='CSE', semester='Spring 2025',
    )

def make_feedback(student, course, **kw):
    defaults = dict(teaching_rating=4, content_rating=4, communication_rating=4)
    defaults.update(kw)
    return Feedback.objects.create(student=student, course=course, **defaults)


#    Faculty Feedback Submission
class FeedbackResponseModelTest(TestCase):


    def setUp(self):
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101011')
        self.course  = make_course(self.faculty)
        self.fb      = make_feedback(self.student, self.course)

    def test_response_created_and_linked(self):

        resp = FeedbackResponse.objects.create(
            feedback=self.fb, faculty=self.faculty, response_text='Thank you!'
        )
        self.assertEqual(FeedbackResponse.objects.count(), 1)
        self.assertEqual(resp.feedback, self.fb)

    def test_duplicate_response_blocked(self):

        FeedbackResponse.objects.create(
            feedback=self.fb, faculty=self.faculty, response_text='First'
        )
        with self.assertRaises(Exception):
            FeedbackResponse.objects.create(
                feedback=self.fb, faculty=self.faculty, response_text='Second'
            )


class FacultyFeedbackListViewTest(TestCase):


    def setUp(self):
        self.client  = Client()
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101013')
        make_course(self.faculty)
        self.url = reverse('faculty_feedback_list')

    def test_unauthenticated_user_redirected(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_faculty_can_access_list(self):
        self.client.login(username='faculty@uap-bd.edu', password='Test@1234')
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_student_cannot_access_faculty_list(self):
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        self.assertEqual(self.client.get(self.url).status_code, 302)


class RespondToFeedbackViewTest(TestCase):


    def setUp(self):
        self.client  = Client()
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101014')
        self.course  = make_course(self.faculty)
        self.fb      = make_feedback(self.student, self.course)
        self.url     = reverse('respond_to_feedback', args=[self.fb.id])

    def test_faculty_response_changes_status(self):

        self.client.login(username='faculty@uap-bd.edu', password='Test@1234')
        self.client.post(self.url, {'response_text': 'Thanks!'})
        self.fb.refresh_from_db()
        self.assertEqual(self.fb.status, 'Responded')

    def test_faculty_response_creates_response_object(self):
        self.client.login(username='faculty@uap-bd.edu', password='Test@1234')
        self.client.post(self.url, {'response_text': 'Thanks!'})
        self.assertEqual(FeedbackResponse.objects.count(), 1)

    def test_student_cannot_access_respond_view(self):
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        self.assertEqual(self.client.get(self.url).status_code, 302)


class MarkFeedbackReviewedViewTest(TestCase):


    def setUp(self):
        self.client  = Client()
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101015')
        self.course  = make_course(self.faculty)
        self.fb      = make_feedback(self.student, self.course)
        self.url     = reverse('mark_feedback_reviewed', args=[self.fb.id])

    def test_faculty_can_mark_reviewed(self):
        self.client.login(username='faculty@uap-bd.edu', password='Test@1234')
        self.client.get(self.url)
        self.fb.refresh_from_db()
        self.assertEqual(self.fb.status, 'Reviewed')

    def test_mark_reviewed_sets_reviewed_at(self):
        self.client.login(username='faculty@uap-bd.edu', password='Test@1234')
        self.client.get(self.url)
        self.fb.refresh_from_db()
        self.assertIsNotNone(self.fb.reviewed_at)


