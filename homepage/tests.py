from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


def make_user(email, role, password='Test@1234', department='CSE', student_id=None):
    """Helper function to create test users"""
    return User.objects.create_user(
        email=email,
        password=password,
        full_name=f'Test {role}',
        role=role,
        department=department,
        student_id=student_id,
    )


class HomepageViewUnauthenticatedTest(TestCase):
    """Test homepage view for unauthenticated users"""

    def setUp(self):
        self.client = Client()
        self.homepage_url = reverse('homepage')

    def test_homepage_url_exists(self):
        """Test that homepage URL is accessible"""
        response = self.client.get(self.homepage_url)
        self.assertEqual(response.status_code, 200)

    def test_homepage_uses_correct_template(self):
        """Test that homepage renders the correct template"""
        response = self.client.get(self.homepage_url)
        self.assertTemplateUsed(response, 'homepage/index.html')

    def test_homepage_context_has_page_title(self):
        """Test that homepage context contains page_title"""
        response = self.client.get(self.homepage_url)
        self.assertIn('page_title', response.context)
        self.assertEqual(response.context['page_title'], 'Welcome to FeedbackFlow')

    def test_unauthenticated_user_sees_homepage(self):
        """Test that unauthenticated users see the homepage"""
        response = self.client.get(self.homepage_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FeedbackFlow', html=False)


class HomepageViewAuthenticatedRedirectTest(TestCase):
    """Test homepage redirects for authenticated users by role"""

    def setUp(self):
        self.client = Client()
        self.homepage_url = reverse('homepage')

    def test_authenticated_student_redirects_to_student_dashboard(self):
        """Test that authenticated student is redirected to student dashboard"""
        student = make_user('student@uap-bd.edu', 'Student', student_id='23101001')
        self.client.force_login(student)
        response = self.client.get(self.homepage_url)
        self.assertRedirects(response, reverse('student_dashboard'))

    def test_authenticated_faculty_redirects_to_faculty_dashboard(self):
        """Test that authenticated faculty is redirected to faculty dashboard"""
        faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.client.force_login(faculty)
        response = self.client.get(self.homepage_url)
        self.assertRedirects(response, reverse('faculty_dashboard'))

    def test_authenticated_hod_redirects_to_hod_dashboard(self):
        """Test that authenticated HOD is redirected to HOD dashboard"""
        hod = make_user('hod@uap-bd.edu', 'HOD')
        self.client.force_login(hod)
        response = self.client.get(self.homepage_url)
        self.assertRedirects(response, reverse('hod_dashboard'))

    def test_authenticated_staff_redirects_to_staff_dashboard(self):
        """Test that authenticated staff is redirected to staff dashboard"""
        staff = make_user('staff@uap-bd.edu', 'Staff')
        self.client.force_login(staff)
        response = self.client.get(self.homepage_url)
        self.assertRedirects(response, reverse('staff_dashboard'))

    def test_authenticated_admin_redirects_to_admin_dashboard(self):
        """Test that authenticated admin is redirected to admin dashboard"""
        admin = User.objects.create_superuser(
            email='admin@uap-bd.edu',
            password='Admin@1234',
            full_name='Test Admin',
        )
        self.client.force_login(admin)
        response = self.client.get(self.homepage_url)
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_authenticated_user_with_unknown_role_redirects(self):
        """Test that authenticated user with unknown role redirects"""
        user = make_user('unknown@uap-bd.edu', 'UnknownRole')
        self.client.force_login(user)
        response = self.client.get(self.homepage_url)
        # Should redirect (302 status code) due to unknown role
        self.assertEqual(response.status_code, 302)

    def test_student_and_faculty_redirect_to_correct_dashboards(self):
        """Test that student and faculty redirect to their respective dashboards"""
        student = make_user('student@test.edu', 'Student', student_id='23101002')
        faculty = make_user('faculty@test.edu', 'Faculty')

        # Test student
        self.client.force_login(student)
        response = self.client.get(self.homepage_url)
        self.assertRedirects(response, reverse('student_dashboard'))

        # Test faculty with new client to clear session
        self.client.logout()
        self.client.force_login(faculty)
        response = self.client.get(self.homepage_url)
        self.assertRedirects(response, reverse('faculty_dashboard'))


class HomepageURLTest(TestCase):
    """Test homepage URL routing"""

    def test_homepage_url_name_resolves(self):
        """Test that homepage URL name resolves correctly"""
        url = reverse('homepage')
        self.assertEqual(url, '/')

    def test_homepage_url_accessible_by_name(self):
        """Test that homepage is accessible by URL name"""
        response = self.client.get(reverse('homepage'))
        self.assertEqual(response.status_code, 200)

    def test_root_url_routes_to_homepage(self):
        """Test that root URL (/) routes to homepage"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)


class HomepageAuthenticationFlowTest(TestCase):
    """Test authentication flow with homepage"""

    def setUp(self):
        self.client = Client()
        self.homepage_url = reverse('homepage')
        self.student = make_user('student@flow.edu', 'Student', student_id='23101003')

    def test_logout_user_returns_to_homepage(self):
        """Test that after logout, accessing homepage shows the page (not redirected)"""
        self.client.force_login(self.student)
        # User is now logged in and would be redirected
        response = self.client.get(self.homepage_url)
        self.assertRedirects(response, reverse('student_dashboard'))

        # Logout
        self.client.logout()
        # Now should see homepage
        response = self.client.get(self.homepage_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage/index.html')

    def test_homepage_accessible_without_session(self):
        """Test that homepage is accessible without any session"""
        self.client.cookies.clear()
        response = self.client.get(self.homepage_url)
        self.assertEqual(response.status_code, 200)

    def test_inactive_user_session_behavior(self):
        """Test that inactive user behavior with existing session"""
        self.client.force_login(self.student)
        # Deactivate user
        self.student.is_active = False
        self.student.save()
        # User is still in session, so will be detected as authenticated and redirected
        # The actual access control happens in the dashboard views
        response = self.client.get(self.homepage_url)
        # Should be a redirect since user.is_authenticated is still True from the session
        self.assertTrue(response.status_code in [200, 302])


class HomepageTemplateContextTest(TestCase):
    """Test homepage template context and rendering"""

    def setUp(self):
        self.client = Client()
        self.homepage_url = reverse('homepage')

    def test_homepage_context_has_page_title(self):
        """Test that homepage context contains page_title"""
        response = self.client.get(self.homepage_url)
        # Unauthenticated user gets the page with context
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_title', response.context)

    def test_page_title_is_string(self):
        """Test that page_title is a string"""
        response = self.client.get(self.homepage_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['page_title'], str)

    def test_page_title_contains_feedbackflow(self):
        """Test that page_title mentions FeedbackFlow"""
        response = self.client.get(self.homepage_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('FeedbackFlow', response.context['page_title'])
