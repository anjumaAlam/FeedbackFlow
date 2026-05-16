from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from feedback.models import Course, CourseAssignment, Feedback, FeedbackResponse, CourseRegistration

User = get_user_model()




def make_user(email, role, department='CSE', **kwargs):
    return User.objects.create_user(
        email=email, password='Test@1234',
        full_name=f'Test {role}', role=role,
        department=department, **kwargs
    )

def make_course(faculty, code='CSE101'):
    course = Course.objects.create(
        course_code=code, course_name='Intro to CS',
        department='CSE', semester='Spring 2025',
    )
    if faculty is not None:
        CourseAssignment.objects.create(
            course=course,
            faculty=faculty,
            is_primary=True
        )
    return course

def make_feedback(student, course, **kw):
    defaults = dict(teaching_rating=4, content_rating=4, communication_rating=4)
    defaults.update(kw)
    return Feedback.objects.create(student=student, course=course, **defaults)



#Course Feedback Submission


class CourseModelTest(TestCase):
    """FEED-12 | Course model unit tests"""

    def setUp(self):
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')

    def test_course_creation(self):
        """Course saves with correct code"""
        course = make_course(self.faculty)
        self.assertEqual(Course.objects.count(), 1)
        self.assertEqual(course.course_code, 'CSE101')

    def test_course_str(self):
        """_str_ includes code and name"""
        course = make_course(self.faculty)
        self.assertIn('CSE101', str(course))
        self.assertIn('Intro to CS', str(course))

    def test_course_is_active_by_default(self):
        """New course defaults to active"""
        self.assertTrue(make_course(self.faculty).is_active)


class CourseFeedbackModelTest(TestCase):
    """FEED-12 | Feedback model unit tests"""

    def setUp(self):
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101010')
        self.course = make_course(self.faculty)

    def test_feedback_saved_correctly(self):
        """Feedback record is persisted"""
        make_feedback(self.student, self.course)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_default_status_is_pending(self):
        """Newly submitted feedback has Pending status"""
        self.assertEqual(make_feedback(self.student, self.course).status, 'Pending')

    def test_get_average_rating(self):
        """Average rating computed correctly: (4+3+5)/3 = 4.0"""
        fb = make_feedback(self.student, self.course,
                           teaching_rating=4, content_rating=3, communication_rating=5)
        self.assertEqual(fb.get_average_rating(), 4.0)

    def test_duplicate_submission_blocked(self):
        """Same student cannot submit feedback twice for same course"""
        make_feedback(self.student, self.course)
        with self.assertRaises(Exception):
            make_feedback(self.student, self.course)

    def test_feedback_str(self):
        """_str_ mentions student email and course code"""
        fb = make_feedback(self.student, self.course)
        self.assertIn('student@uap-bd.edu', str(fb))
        self.assertIn('CSE101', str(fb))


class SubmitCourseFeedbackViewTest(TestCase):
    """FEED-12 | submit_feedback view tests"""

    def setUp(self):
        self.client = Client()
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101012')
        self.course = make_course(self.faculty)
        
        # Register the student for the course
        from feedback.models import CourseRegistration
        CourseRegistration.objects.create(
            student=self.student,
            course=self.course,
            is_confirmed=True
        )
        
        # Create course assignment
        CourseAssignment.objects.create(
            course=self.course,
            faculty=self.faculty,
            class_section='A',
            is_primary=True
        )
        
        self.url = reverse('submit_feedback')

    def test_unauthenticated_user_redirected(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_student_sees_feedback_form(self):
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_valid_post_creates_feedback(self):
        """Valid form submission creates a Feedback object"""
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        self.client.post(self.url, {
            'course': self.course.id,
            'faculty': self.faculty.id,
            'class_section': 'A',
            'teaching_rating': 4, 'content_rating': 4,
            'communication_rating': 5, 'is_anonymous': False,
        })
        self.assertEqual(Feedback.objects.count(), 1)

    def test_successful_submission_redirects(self):
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        response = self.client.post(self.url, {
            'course': self.course.id,
            'faculty': self.faculty.id,
            'class_section': 'A',
            'teaching_rating': 3, 'content_rating': 3,
            'communication_rating': 3, 'is_anonymous': False,
        })
        self.assertEqual(response.status_code, 302)

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
        self.course = make_course(self.faculty)
        # Create feedback assigned to the faculty
        self.fb = make_feedback(self.student, self.course)
        self.fb.faculty = self.faculty
        self.fb.save()
        self.url = reverse('faculty_feedback_list')

    def test_unauthenticated_user_redirected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_faculty_can_view_feedback(self):
        """Faculty can view feedback assigned to them"""
        self.client.login(username='faculty@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.fb, response.context.get('feedback_list', []))


class CourseRegistrationModelTest(TestCase):
    """Tests for CourseRegistration model"""

    def setUp(self):
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101014')
        self.course = make_course(self.faculty)

    def test_course_registration_created(self):
        """CourseRegistration can be created and linked"""
        reg = CourseRegistration.objects.create(
            student=self.student,
            course=self.course,
            is_confirmed=True
        )
        self.assertEqual(CourseRegistration.objects.count(), 1)
        self.assertEqual(reg.student, self.student)

    def test_duplicate_registration_blocked(self):
        """Student cannot register for same course twice"""
        CourseRegistration.objects.create(
            student=self.student,
            course=self.course,
            is_confirmed=True
        )
        with self.assertRaises(Exception):
            CourseRegistration.objects.create(
                student=self.student,
                course=self.course,
                is_confirmed=True
            )

    def test_registration_str(self):
        """__str__ includes student and course info"""
        reg = CourseRegistration.objects.create(
            student=self.student,
            course=self.course,
            is_confirmed=True
        )
        self.assertIn(self.student.full_name, str(reg))
        self.assertIn(self.course.course_code, str(reg))


class FeedbackRatingValidationTest(TestCase):
    """Tests for rating validation in Feedback model"""

    def setUp(self):
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101015')
        self.course = make_course(self.faculty)

    def test_rating_min_value_enforced(self):
        """Ratings cannot be less than 1"""
        with self.assertRaises(Exception):
            Feedback.objects.create(
                student=self.student,
                course=self.course,
                teaching_rating=0,  # Invalid
                content_rating=3,
                communication_rating=3
            )

    def test_rating_max_value_enforced(self):
        """Ratings cannot exceed 5"""
        with self.assertRaises(Exception):
            Feedback.objects.create(
                student=self.student,
                course=self.course,
                teaching_rating=6,  # Invalid
                content_rating=3,
                communication_rating=3
            )


class CourseAssignmentTest(TestCase):
    """Tests for CourseAssignment model"""

    def setUp(self):
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.course = make_course(self.faculty)

    def test_primary_assignment_flag(self):
        """Can mark a CourseAssignment as primary"""
        assignment = CourseAssignment.objects.get(course=self.course)
        self.assertTrue(assignment.is_primary)

    def test_section_assignment(self):
        """Can assign faculty to specific section"""
        assignment = CourseAssignment.objects.create(
            course=self.course,
            faculty=self.faculty,
            class_section='B',
            is_primary=False
        )
        self.assertEqual(assignment.class_section, 'B')

    def test_get_primary_faculty_method(self):
        """Course.get_primary_faculty returns primary faculty"""
        primary = self.course.get_primary_faculty()
        self.assertEqual(primary, self.faculty)

    def test_get_faculty_names_method(self):
        """Course.get_faculty_names returns comma-separated faculty names"""
        names = self.course.get_faculty_names()
        self.assertIn(self.faculty.full_name, names)


class MyFeedbackViewTest(TestCase):
    """Tests for my_feedback view"""

    def setUp(self):
        self.client = Client()
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101016')
        self.course = make_course(self.faculty)
        self.feedback = make_feedback(self.student, self.course)
        self.url = reverse('my_feedback')

    def test_unauthenticated_user_redirected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_student_sees_own_feedback(self):
        """Student can view their own feedback"""
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_only_students_can_access(self):
        """Non-students are denied access"""
        self.client.login(username='faculty@uap-bd.edu', password='Test@1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class FeedbackDetailViewTest(TestCase):
    """Tests for feedback_detail view"""

    def setUp(self):
        self.client = Client()
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101017')
        self.other_student = make_user('other@uap-bd.edu', 'Student', student_id='23101018')
        self.course = make_course(self.faculty)
        self.feedback = make_feedback(self.student, self.course)

    def test_unauthenticated_user_redirected(self):
        url = reverse('feedback_detail', args=[self.feedback.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_student_can_view_own_feedback(self):
        """Student can view their own feedback"""
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        url = reverse('feedback_detail', args=[self.feedback.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_view_others_feedback(self):
        """Student cannot view another student's feedback"""
        self.client.login(username='other@uap-bd.edu', password='Test@1234')
        url = reverse('feedback_detail', args=[self.feedback.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

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
        # Set faculty on feedback
        self.fb.faculty = self.faculty
        self.fb.save()
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
        # Set faculty on feedback
        self.fb.faculty = self.faculty
        self.fb.save()
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



# Anonymous Feedback


class AnonymousFeedbackModelTest(TestCase):
    """FEED-14 | Anonymous flag on the Feedback model"""

    def setUp(self):
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101020')
        self.course = make_course(self.faculty)

    def test_is_anonymous_defaults_to_false(self):
        fb = make_feedback(self.student, self.course)
        self.assertFalse(fb.is_anonymous)

    def test_anonymous_flag_saved_correctly(self):
        fb = make_feedback(self.student, self.course, is_anonymous=True)
        fb.refresh_from_db()
        self.assertTrue(fb.is_anonymous)

    def test_anonymous_feedback_still_links_to_student(self):
        """Even anonymous feedback records the actual student server-side"""
        fb = make_feedback(self.student, self.course, is_anonymous=True)
        self.assertEqual(fb.student, self.student)

    def test_non_anonymous_exposes_student(self):
        fb = make_feedback(self.student, self.course, is_anonymous=False)
        self.assertEqual(fb.student.email, 'student@uap-bd.edu')


class AnonymousFeedbackSubmissionViewTest(TestCase):
    """FEED-14 | Submitting anonymous feedback through the view"""

    def setUp(self):
        self.client = Client()
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101021')
        self.course = make_course(self.faculty)
        
        # Register the student for the course
        CourseRegistration.objects.create(
            student=self.student,
            course=self.course,
            is_confirmed=True
        )
        
        # Create course assignment
        CourseAssignment.objects.create(
            course=self.course,
            faculty=self.faculty,
            class_section='A',
            is_primary=True
        )
        
        self.url = reverse('submit_feedback')

    def test_anonymous_submission_creates_feedback(self):
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        self.client.post(self.url, {
            'course': self.course.id,
            'faculty': self.faculty.id,
            'class_section': 'A',
            'teaching_rating': 3, 'content_rating': 3,
            'communication_rating': 3, 'is_anonymous': True,
        })
        self.assertEqual(Feedback.objects.count(), 1)

    def test_anonymous_flag_persisted_via_view(self):
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        self.client.post(self.url, {
            'course': self.course.id,
            'faculty': self.faculty.id,
            'class_section': 'A',
            'teaching_rating': 5, 'content_rating': 5,
            'communication_rating': 5, 'is_anonymous': True,
        })
        fb = Feedback.objects.first()
        self.assertIsNotNone(fb)
        self.assertTrue(fb.is_anonymous)

    def test_anonymous_feedback_redirects_on_success(self):
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        response = self.client.post(self.url, {
            'course': self.course.id,
            'faculty': self.faculty.id,
            'class_section': 'A',
            'teaching_rating': 4, 'content_rating': 4,
            'communication_rating': 4, 'is_anonymous': True,
        })
        self.assertEqual(response.status_code, 302)

    def test_anonymous_feedback_visible_in_my_feedback(self):
        """Anonymous entry still appears in the student's own list"""
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        make_feedback(self.student, self.course, is_anonymous=True)
        response = self.client.get(reverse('my_feedback'))
        self.assertEqual(response.status_code, 200)
        courses = [fb.course for fb in response.context['feedback_list']]
        self.assertIn(self.course, courses)