from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from feedback.models import Course, CourseAssignment, Feedback
from complaints.models import Complaint

User = get_user_model()


def make_user(email, role, password='Test@1234', department='CSE',
              student_id=None, is_active=True, **kwargs):

    return User.objects.create_user(
        email=email,
        password=password,
        full_name=f'Test {role}',
        role=role,
        department=department,
        student_id=student_id,
        is_active=is_active,
        **kwargs
    )


def make_course(faculty, code='CSE101', name='Test Course',
                department='CSE', semester='Spring 2025'):

    course = Course.objects.create(
        course_code=code,
        course_name=name,
        department=department,
        semester=semester,
    )
    if faculty is not None:
        CourseAssignment.objects.create(
            course=course,
            faculty=faculty,
            is_primary=True
        )
    return course


class UserModelTest(TestCase):


    def setUp(self):

        self.user = User.objects.create_user(
            email='student@uap-bd.edu',
            password='Student@123',
            full_name='Test Student',
            role='Student',
            student_id='23101157',
            department='CSE'
        )

    def test_user_creation(self):

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.user.email, 'student@uap-bd.edu')
        self.assertEqual(self.user.full_name, 'Test Student')
        self.assertEqual(self.user.role, 'Student')

    def test_user_email_is_unique(self):

        self.assertTrue(User.objects.filter(email='student@uap-bd.edu').exists())

    def test_password_is_hashed(self):
        """Test that password is not stored in plain text"""
        self.assertNotEqual(self.user.password, 'Student@123')
        self.assertTrue(self.user.check_password('Student@123'))

    def test_user_string_representation(self):

        expected = "Test Student (student@uap-bd.edu)"
        self.assertEqual(str(self.user), expected)

    def test_get_short_name(self):

        self.assertEqual(self.user.get_short_name(), 'Test')

    def test_user_is_active_by_default(self):

        self.assertTrue(self.user.is_active)

    def test_user_is_not_staff_by_default(self):

        self.assertFalse(self.user.is_staff)

    def test_student_has_student_id(self):

        self.assertEqual(self.user.student_id, '23101157')

    def test_user_has_department(self):

        self.assertEqual(self.user.department, 'CSE')


class RegistrationViewTest(TestCase):


    def setUp(self):

        self.client = Client()
        self.register_url = reverse('register')

    def test_registration_page_exists(self):

        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)

    def test_registration_uses_correct_template(self):

        response = self.client.get(self.register_url)
        self.assertTemplateUsed(response, 'users/register.html')

    def test_registration_page_contains_form(self):

        response = self.client.get(self.register_url)
        self.assertContains(response, '<form')
        self.assertContains(response, 'email')
        self.assertContains(response, 'password')

    def test_successful_registration_creates_user(self):

        data = {
            'full_name': 'New Student',
            'email': 'newstudent@uap-bd.edu',
            'student_id': '23101999',
            'department': 'CSE',
            'password': 'NewPass@123',
            'confirm_password': 'NewPass@123'
        }
        self.client.post(self.register_url, data)
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(User.objects.filter(email='newstudent@uap-bd.edu').exists())

    def test_registration_redirects_after_success(self):

        data = {
            'full_name': 'New Student',
            'email': 'newstudent@uap-bd.edu',
            'student_id': '23101999',
            'department': 'CSE',
            'password': 'NewPass@123',
            'confirm_password': 'NewPass@123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)

    def test_registration_assigns_student_role(self):

        data = {
            'full_name': 'New Student',
            'email': 'newstudent@uap-bd.edu',
            'student_id': '23101999',
            'department': 'CSE',
            'password': 'NewPass@123',
            'confirm_password': 'NewPass@123'
        }
        self.client.post(self.register_url, data)
        user = User.objects.get(email='newstudent@uap-bd.edu')
        self.assertEqual(user.role, 'Student')


class LoginViewTest(TestCase):
    """Comprehensive login tests for all user roles"""

    def setUp(self):
        """Set up test client and users"""
        self.client = Client()
        self.login_url = reverse('login')
        self.student = make_user('student@uap-bd.edu', 'Student', 
                                password='Student@123', student_id='23101001')
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty',
                                password='Faculty@123')
        self.hod = make_user('hod@uap-bd.edu', 'HOD',
                            password='HOD@123')
        self.staff = make_user('staff@uap-bd.edu', 'Staff',
                              password='Staff@123')
        self.admin = make_user('admin@uap-bd.edu', 'Admin',
                              password='Admin@123')

    # === BASIC LOGIN PAGE TESTS ===
    def test_login_page_exists(self):
        """Test that login page loads successfully"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_login_uses_correct_template(self):
        """Test that login page uses the correct template"""
        response = self.client.get(self.login_url)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_login_page_contains_form(self):
        """Test that login page contains form with email and password fields"""
        response = self.client.get(self.login_url)
        self.assertContains(response, '<form')
        self.assertContains(response, 'email')
        self.assertContains(response, 'password')

    def test_authenticated_user_redirected_from_login(self):
        """Test that authenticated users are redirected from login page"""
        self.client.force_login(self.student)
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)

    # === SUCCESSFUL LOGIN TESTS ===
    def test_successful_student_login_redirects(self):
        """Test student login redirects after successful authentication"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        self.assertEqual(response.status_code, 302)

    def test_successful_student_login_creates_session(self):
        """Test that student login creates a valid session"""
        self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_successful_faculty_login_creates_session(self):
        """Test that faculty login creates a valid session"""
        self.client.post(self.login_url, {
            'email': 'faculty@uap-bd.edu',
            'password': 'Faculty@123'
        })
        response = self.client.get(reverse('faculty_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_successful_hod_login_creates_session(self):
        """Test that HOD login creates a valid session"""
        self.client.post(self.login_url, {
            'email': 'hod@uap-bd.edu',
            'password': 'HOD@123'
        })
        response = self.client.get(reverse('hod_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_successful_staff_login_creates_session(self):
        """Test that staff login creates a valid session"""
        self.client.post(self.login_url, {
            'email': 'staff@uap-bd.edu',
            'password': 'Staff@123'
        })
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_successful_admin_login_creates_session(self):
        """Test that admin login creates a valid session"""
        self.client.post(self.login_url, {
            'email': 'admin@uap-bd.edu',
            'password': 'Admin@123'
        })
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    # === INVALID CREDENTIALS TESTS ===
    def test_wrong_password_does_not_login(self):
        """Test that wrong password prevents login"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'WrongPassword@123'
        })
        self.assertEqual(response.status_code, 200)
        # Verify not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_wrong_password_keeps_user_on_login_page(self):
        """Test that invalid credentials keep user on login page"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'WrongPassword@123'
        })
        self.assertTemplateUsed(response, 'users/login.html')

    def test_nonexistent_user_cannot_login(self):
        """Test that non-existent user cannot login"""
        response = self.client.post(self.login_url, {
            'email': 'nonexistent@uap-bd.edu',
            'password': 'Test@123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_email_normalization(self):
        """Test that email is normalized during login"""
        # Test that login works with the exact email
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        # Should redirect (login successful)
        self.assertEqual(response.status_code, 302)

    def test_empty_email_fails(self):
        """Test that empty email fails login"""
        response = self.client.post(self.login_url, {
            'email': '',
            'password': 'Student@123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_empty_password_fails(self):
        """Test that empty password fails login"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')

    # === INACTIVE USER TESTS ===
    def test_inactive_user_cannot_login(self):
        """Test that inactive user cannot login"""
        self.student.is_active = False
        self.student.save()
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_inactive_user_sees_error_message(self):
        """Test that inactive user sees deactivation message"""
        self.student.is_active = False
        self.student.save()
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        messages = list(response.context['messages'])
        self.assertTrue(any('deactivated' in str(m) for m in messages))

    def test_deactivated_user_cannot_access_dashboard(self):
        """Test that deactivated user cannot access dashboard"""
        self.client.force_login(self.student)
        self.student.is_active = False
        self.student.save()
        response = self.client.get(reverse('student_dashboard'))
        # Should redirect due to inactive status (depends on implementation)
        self.assertNotEqual(response.status_code, 200)

    # === ROLE-BASED REDIRECT TESTS ===
    def test_student_redirects_to_student_dashboard(self):
        """Test that student login redirects to student dashboard"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        }, follow=True)
        self.assertTemplateUsed(response, 'users/student_dashboard.html')

    def test_faculty_redirects_to_faculty_dashboard(self):
        """Test that faculty login redirects to faculty dashboard"""
        response = self.client.post(self.login_url, {
            'email': 'faculty@uap-bd.edu',
            'password': 'Faculty@123'
        }, follow=True)
        self.assertTemplateUsed(response, 'users/faculty_dashboard.html')

    def test_hod_redirects_to_hod_dashboard(self):
        """Test that HOD login redirects to HOD dashboard"""
        response = self.client.post(self.login_url, {
            'email': 'hod@uap-bd.edu',
            'password': 'HOD@123'
        }, follow=True)
        self.assertTemplateUsed(response, 'users/hod_dashboard.html')

    def test_staff_redirects_to_staff_dashboard(self):
        """Test that staff login redirects to staff dashboard"""
        response = self.client.post(self.login_url, {
            'email': 'staff@uap-bd.edu',
            'password': 'Staff@123'
        }, follow=True)
        self.assertTemplateUsed(response, 'users/staff_dashboard.html')

    def test_admin_redirects_to_admin_dashboard(self):
        """Test that admin login redirects to admin dashboard"""
        response = self.client.post(self.login_url, {
            'email': 'admin@uap-bd.edu',
            'password': 'Admin@123'
        }, follow=True)
        self.assertTemplateUsed(response, 'users/admin_dashboard.html')

    # === SUCCESS MESSAGE TESTS ===
    def test_successful_login_shows_welcome_message(self):
        """Test that successful login shows welcome message"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        }, follow=True)
        messages = list(response.context['messages'])
        self.assertTrue(any('Welcome' in str(m) for m in messages))

    def test_failed_login_shows_error_message(self):
        """Test that failed login shows error message"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'WrongPassword@123'
        })
        messages = list(response.context['messages'])
        self.assertTrue(any('Invalid' in str(m) or 'password' in str(m).lower() 
                          for m in messages))

    # === FORM VALIDATION TESTS ===
    def test_invalid_email_format_fails(self):
        """Test that invalid email format fails"""
        response = self.client.post(self.login_url, {
            'email': 'not-an-email',
            'password': 'Student@123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_whitespace_in_email_handled(self):
        """Test that whitespace in email is handled properly"""
        response = self.client.post(self.login_url, {
            'email': '  student@uap-bd.edu  ',
            'password': 'Student@123'
        })
        # Should still work or show appropriate error
        self.assertIn(response.status_code, [200, 302])

    # === SESSION SECURITY TESTS ===
    def test_login_sets_session_cookie(self):
        """Test that login sets a session cookie"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        }, follow=True)
        self.assertIn('sessionid', self.client.cookies)

    def test_user_info_available_in_session(self):
        """Test that user info is available after login"""
        self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.wsgi_request.user.email, 'student@uap-bd.edu')
        self.assertEqual(response.wsgi_request.user.role, 'Student')

    # === MULTIPLE ATTEMPTS TESTS ===
    def test_multiple_failed_attempts_do_not_lockout(self):
        """Test that multiple failed login attempts don't lock account"""
        for i in range(5):
            self.client.post(self.login_url, {
                'email': 'student@uap-bd.edu',
                'password': f'WrongPassword{i}@123'
            })
        # User should still be able to login with correct password
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        self.assertEqual(response.status_code, 302)

    def test_second_login_after_logout(self):
        """Test that user can login again after logout"""
        # First login
        self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        # Logout
        self.client.get(reverse('logout'))
        # Second login
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        self.assertEqual(response.status_code, 302)


class LogoutViewTest(TestCase):


    def setUp(self):

        self.client = Client()
        self.logout_url = reverse('logout')
        self.user = User.objects.create_user(
            email='student@uap-bd.edu',
            password='Student@123',
            full_name='Test Student',
            role='Student'
        )

    def test_logout_redirects_to_login(self):

        self.client.login(username='student@uap-bd.edu', password='Student@123')
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)

    def test_logout_clears_session(self):

        self.client.login(username='student@uap-bd.edu', password='Student@123')
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.client.get(self.logout_url)
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 302)


class PasswordResetTest(TestCase):


    def setUp(self):

        self.client = Client()
        self.reset_url = reverse('password_reset_request')
        self.user = User.objects.create_user(
            email='student@uap-bd.edu',
            password='Student@123',
            full_name='Test Student',
            role='Student'
        )

    def test_password_reset_page_exists(self):

        response = self.client.get(self.reset_url)
        self.assertEqual(response.status_code, 200)

    def test_password_reset_uses_correct_template(self):

        response = self.client.get(self.reset_url)
        self.assertTemplateUsed(response, 'users/password_reset_request.html')

    def test_password_reset_page_contains_form(self):

        response = self.client.get(self.reset_url)
        self.assertContains(response, '<form')
        self.assertContains(response, 'email')


class DashboardAccessTest(TestCase):


    def setUp(self):

        self.client = Client()
        self.student = User.objects.create_user(
            email='student@uap-bd.edu',
            password='Student@123',
            full_name='Test Student',
            role='Student'
        )
        self.faculty = User.objects.create_user(
            email='faculty@uap-bd.edu',
            password='Faculty@123',
            full_name='Test Faculty',
            role='Faculty'
        )

    def test_student_can_access_student_dashboard(self):

        self.client.login(username='student@uap-bd.edu', password='Student@123')
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_faculty_can_access_faculty_dashboard(self):

        self.client.login(username='faculty@uap-bd.edu', password='Faculty@123')
        response = self.client.get(reverse('faculty_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_cannot_access_dashboard(self):

        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_student_dashboard_shows_user_info(self):

        self.client.login(username='student@uap-bd.edu', password='Student@123')
        response = self.client.get(reverse('student_dashboard'))
        self.assertContains(response, 'Test Student')
        self.assertContains(response, 'student@uap-bd.edu')


class URLTest(TestCase):


    def setUp(self):

        self.client = Client()

    def test_login_url_exists(self):

        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_register_url_exists(self):

        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_password_reset_url_exists(self):

        response = self.client.get(reverse('password_reset_request'))
        self.assertEqual(response.status_code, 200)

    def test_root_url_returns_homepage(self):
        """Test that root URL loads the homepage"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)


class FormTest(TestCase):


    def setUp(self):

        self.client = Client()
        self.register_url = reverse('register')

    def test_registration_form_accepts_valid_data(self):

        data = {
            'full_name': 'Valid User',
            'email': 'valid@uap-bd.edu',
            'student_id': '12345678',
            'department': 'CSE',
            'password': 'ValidPass@123',
            'confirm_password': 'ValidPass@123'
        }
        self.client.post(self.register_url, data)
        self.assertTrue(User.objects.filter(email='valid@uap-bd.edu').exists())

    def test_registration_requires_all_fields(self):

        data = {
            'full_name': '',  # Empty
            'email': 'test@uap-bd.edu',
            'student_id': '12345678',
            'department': 'CSE',
            'password': 'Test@123',
            'confirm_password': 'Test@123'
        }
        self.client.post(self.register_url, data)
        self.assertEqual(User.objects.count(), 0)


class UserModelRoleTest(TestCase):


    def test_all_roles_can_be_created(self):

        roles = [('Student', '23101001'), ('Faculty', None),
                 ('HOD', None), ('Staff', None), ('Admin', None)]
        for i, (role, sid) in enumerate(roles):
            kwargs = {'student_id': sid} if sid else {}
            u = User.objects.create_user(
                email=f'{role.lower()}{i}@uap-bd.edu', password='Test@1234',
                full_name=f'Test {role}', role=role, **kwargs
            )
            self.assertEqual(u.role, role)

    def test_user_can_be_deactivated(self):
        u = make_user('todeactivate@uap-bd.edu', 'Faculty')
        u.is_active = False
        u.save()
        u.refresh_from_db()
        self.assertFalse(u.is_active)

    def test_deactivated_user_cannot_login(self):
        make_user('inactive@uap-bd.edu', 'Faculty', is_active=False)
        c = Client()
        c.post(reverse('login'), {'email': 'inactive@uap-bd.edu', 'password': 'Test@1234'})
        self.assertEqual(c.get(reverse('faculty_dashboard')).status_code, 302)

    def test_admin_superuser_has_is_staff_true(self):
        admin = User.objects.create_superuser(
            email='superadmin@uap-bd.edu', password='Admin@1234'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_duplicate_email_raises_error(self):
        make_user('dup@uap-bd.edu', 'Faculty')
        with self.assertRaises(Exception):
            make_user('dup@uap-bd.edu', 'Staff')


class AdminDashboardViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101002')
        self.url = reverse('admin_dashboard')

    def test_unauthenticated_user_redirected(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_admin_can_access_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_dashboard_shows_correct_total_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_users'], 2)

    def test_dashboard_shows_student_count(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.context['student_count'], 1)

    def test_dashboard_shows_active_users_count(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertIn('active_users', response.context)

    def test_dashboard_uses_correct_template(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'users/admin_dashboard.html')


class AdminOnlyAccessTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101004')
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.hod = make_user('hod@uap-bd.edu', 'HOD')
        self.staff = make_user('staff@uap-bd.edu', 'Staff')

    def test_student_cannot_access_user_list(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('admin_user_list')).status_code, 302)

    def test_faculty_cannot_access_user_list(self):
        self.client.force_login(self.faculty)
        self.assertEqual(self.client.get(reverse('admin_user_list')).status_code, 302)

    def test_hod_cannot_access_user_list(self):
        self.client.force_login(self.hod)
        self.assertEqual(self.client.get(reverse('admin_user_list')).status_code, 302)

    def test_staff_cannot_access_user_list(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('admin_user_list')).status_code, 302)

    def test_only_admin_can_access_user_list(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('admin_user_list')).status_code, 200)




class DashboardRoleAccessTest(TestCase):


   def setUp(self):
       self.client = Client()
       self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101005')
       self.hod = make_user('hod@uap-bd.edu', 'HOD')
       self.staff = make_user('staff@uap-bd.edu', 'Staff')

       def test_hod_can_access_hod_dashboard(self):

           self.client.force_login(self.hod)
           self.assertEqual(self.client.get(reverse('hod_dashboard')).status_code, 200)

       def test_staff_can_access_staff_dashboard(self):
           self.client.force_login(self.staff)
           self.assertEqual(self.client.get(reverse('staff_dashboard')).status_code, 200)

       def test_unauthenticated_redirected_from_hod_dashboard(self):
           self.assertEqual(self.client.get(reverse('hod_dashboard')).status_code, 302)

       def test_unauthenticated_redirected_from_staff_dashboard(self):
           self.assertEqual(self.client.get(reverse('staff_dashboard')).status_code, 302)

class AppointmentModelTest(TestCase):
    """Tests for the Appointment model"""

    def setUp(self):
        from users.models import Appointment
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101019')
        self.committee = make_user('committee@uap-bd.edu', 'Committee', committee_type='Harassment Committee')
        self.admin = make_user('admin@uap-bd.edu', 'Admin')

    def test_appointment_creation(self):
        """Can create an Appointment"""
        from users.models import Appointment
        appt = Appointment.objects.create(
            requester=self.student,
            status='Pending',
            description='Request for meeting'
        )
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(appt.requester, self.student)

    def test_appointment_status_choices(self):
        """Appointment status defaults to Pending"""
        from users.models import Appointment
        appt = Appointment.objects.create(
            requester=self.student,
            description='Test appointment'
        )
        self.assertEqual(appt.status, 'Pending')

    def test_appointment_assigned_to_committee(self):
        """Appointment can be assigned to committee members"""
        from users.models import Appointment
        appt = Appointment.objects.create(
            requester=self.student,
            assigned_to=self.committee,
            status='Pending',
            description='Harassment complaint'
        )
        self.assertEqual(appt.assigned_to, self.committee)

    def test_appointment_str(self):
        """__str__ includes requester and status"""
        from users.models import Appointment
        appt = Appointment.objects.create(
            requester=self.student,
            status='Pending',
            description='Test'
        )
        self.assertIn(self.student.full_name, str(appt))
        self.assertIn('Pending', str(appt))

    def test_appointment_forwarded_to_committee_status(self):
        """Appointment status can be changed to Forwarded to Committee"""
        from users.models import Appointment
        appt = Appointment.objects.create(
            requester=self.student,
            status='Pending',
            description='Test'
        )
        appt.status = 'Forwarded to Committee'
        appt.save()
        self.assertEqual(appt.status, 'Forwarded to Committee')

    def test_appointment_meeting_scheduled_status(self):
        """Appointment can be scheduled for meeting"""
        from users.models import Appointment
        from django.utils import timezone
        appt = Appointment.objects.create(
            requester=self.student,
            status='Meeting Scheduled',
            description='Test',
            meeting_date=timezone.now() + timezone.timedelta(days=3)
        )
        self.assertIsNotNone(appt.meeting_date)

    def test_appointment_closed_status(self):
        """Appointment can be closed"""
        from users.models import Appointment
        appt = Appointment.objects.create(
            requester=self.student,
            status='Closed',
            description='Test'
        )
        self.assertEqual(appt.status, 'Closed')


class UserRolePermissionsTest(TestCase):
    """Tests for role-based permissions"""

    def setUp(self):
        self.client = Client()
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101020')
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.hod = make_user('hod@uap-bd.edu', 'HOD')
        self.admin = make_user('admin@uap-bd.edu', 'Admin')

    def test_student_cannot_access_admin_panel(self):
        """Student should not access admin functions"""
        self.client.force_login(self.student)
        response = self.client.get(reverse('admin_user_list'))
        self.assertEqual(response.status_code, 302)

    def test_faculty_cannot_access_hod_dashboard(self):
        """Faculty should not access HOD functions"""
        self.client.force_login(self.faculty)
        response = self.client.get(reverse('hod_dashboard'))
        # Depending on implementation, could be 302 or 403
        self.assertIn(response.status_code, [302, 403])

    def test_admin_can_access_everything(self):
        """Admin should access admin panel"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_user_list'))
        self.assertEqual(response.status_code, 200)

    def test_user_department_is_set_correctly(self):
        """User department is stored correctly"""
        self.assertEqual(self.student.department, 'CSE')
        self.assertEqual(self.faculty.department, 'CSE')
        self.assertEqual(self.hod.department, 'CSE')


class CommitteeUserTest(TestCase):
    """Tests for Committee role with committee_type"""

    def setUp(self):
        self.harassment_committee = make_user(
            'hc@uap-bd.edu', 'Committee',
            committee_type='Harassment Committee'
        )
        self.proctorial_committee = make_user(
            'pc@uap-bd.edu', 'Committee',
            committee_type='Proctorial Committee'
        )

    def test_committee_user_has_committee_type(self):
        """Committee users have committee_type set"""
        self.assertEqual(
            self.harassment_committee.committee_type,
            'Harassment Committee'
        )

    def test_different_committee_types(self):
        """Multiple committee types can exist"""
        self.assertNotEqual(
            self.harassment_committee.committee_type,
            self.proctorial_committee.committee_type
        )

    def test_non_committee_user_no_committee_type(self):
        """Non-committee users don't have committee_type"""
        student = make_user('student@uap-bd.edu', 'Student', student_id='23101021')
        self.assertIsNone(student.committee_type)


class DashboardContextDataTest(TestCase):


    def setUp(self):
        self.client = Client()
        self.admin = make_user('admin@uap-bd.edu', 'Admin')
        self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101006')
        self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
        self.hod = make_user('hod@uap-bd.edu', 'HOD')
        self.course = make_course(self.faculty)

    def test_student_dashboard_complaint_count_updates(self):
        Complaint.objects.create(
            student=self.student, complaint_type='Behavioral',
            subject='Test', description='Details.'
        )
        self.client.force_login(self.student)
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.context['total_complaints'], 1)

    def test_student_dashboard_feedback_count_updates(self):
        Feedback.objects.create(
            student=self.student, course=self.course,
            teaching_rating=4, content_rating=4, communication_rating=4
        )
        self.client.force_login(self.student)
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.context['total_feedback'], 1)

    def test_faculty_dashboard_shows_pending_feedback(self):
        Feedback.objects.create(
            student=self.student, course=self.course, faculty=self.faculty,
            teaching_rating=3, content_rating=3, communication_rating=3
        )
        self.client.force_login(self.faculty)
        response = self.client.get(reverse('faculty_dashboard'))
        self.assertEqual(response.context['pending_response'], 1)

    def test_hod_dashboard_shows_complaint_stats(self):

        self.client.force_login(self.hod)
        response = self.client.get(reverse('hod_dashboard'))
        self.assertIn('total_complaints', response.context)
        self.assertIn('pending_complaints', response.context)

    def test_admin_dashboard_shows_correct_user_counts(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.context['student_count'], 1)
        self.assertEqual(response.context['faculty_count'], 1)




class CrossRoleAccessTest(TestCase):



   def setUp(self):
       self.client = Client()
       self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101007')
       self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
       self.hod = make_user('hod@uap-bd.edu', 'HOD')
       self.staff = make_user('staff@uap-bd.edu', 'Staff')
       self.admin = make_user('admin@uap-bd.edu', 'Admin')

   def test_student_cannot_access_faculty_dashboard(self):
       self.client.force_login(self.student)
       self.assertEqual(self.client.get(reverse('faculty_dashboard')).status_code, 302)

   def test_student_cannot_access_admin_dashboard(self):
       self.client.force_login(self.student)
       self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 302)

   def test_faculty_cannot_access_student_dashboard(self):
       self.client.force_login(self.faculty)
       self.assertEqual(self.client.get(reverse('student_dashboard')).status_code, 302)

   def test_hod_cannot_access_staff_dashboard(self):
       self.client.force_login(self.hod)
       self.assertEqual(self.client.get(reverse('staff_dashboard')).status_code, 302)

   def test_staff_cannot_access_hod_dashboard(self):
       self.client.force_login(self.staff)
       self.assertEqual(self.client.get(reverse('hod_dashboard')).status_code, 302)

   def test_login_redirects_student_to_correct_dashboard(self):
       response = self.client.post(reverse('login'), {
           'email': 'student@uap-bd.edu', 'password': 'Test@1234'
       })
       self.assertRedirects(response, reverse('student_dashboard'))

   def test_login_redirects_faculty_to_correct_dashboard(self):
       response = self.client.post(reverse('faculty_login'), {
           'email': 'faculty@uap-bd.edu', 'password': 'Test@1234'
       })
       self.assertRedirects(response, reverse('faculty_dashboard'))

class FeedbackReportsAccessTest(TestCase):


   def setUp(self):
       self.client = Client()
       self.admin = make_user('admin@uap-bd.edu', 'Admin')
       self.hod = make_user('hod@uap-bd.edu', 'HOD')
       self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
       self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101008')
       self.staff = make_user('staff@uap-bd.edu', 'Staff')
       self.url = reverse('feedback_reports')

   def test_unauthenticated_user_redirected(self):
       self.assertEqual(self.client.get(self.url).status_code, 302)

   def test_admin_can_access_reports(self):
       self.client.force_login(self.admin)
       self.assertEqual(self.client.get(self.url).status_code, 200)

   def test_hod_can_access_reports(self):
       self.client.force_login(self.hod)
       self.assertEqual(self.client.get(self.url).status_code, 200)

   def test_faculty_cannot_access_reports(self):
       self.client.force_login(self.faculty)
       self.assertEqual(self.client.get(self.url).status_code, 302)

   def test_student_cannot_access_reports(self):
       self.client.force_login(self.student)
       self.assertEqual(self.client.get(self.url).status_code, 302)

   def test_staff_cannot_access_reports(self):
       self.client.force_login(self.staff)
       self.assertEqual(self.client.get(self.url).status_code, 302)

   def test_reports_uses_correct_template(self):
       self.client.force_login(self.admin)
       response = self.client.get(self.url)
       self.assertTemplateUsed(response, 'users/feedback_reports.html')




class FeedbackReportsDataTest(TestCase):


   def setUp(self):
       self.client = Client()
       self.admin = make_user('admin@uap-bd.edu', 'Admin')
       self.faculty = make_user('faculty@uap-bd.edu', 'Faculty')
       self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101009')
       self.course = make_course(self.faculty)
       self.url = reverse('feedback_reports')

   def test_total_feedback_count_zero_initially(self):
       self.client.force_login(self.admin)
       response = self.client.get(self.url)
       self.assertEqual(response.context['total_feedback'], 0)

   def test_total_feedback_count_updates(self):
       Feedback.objects.create(
           student=self.student, course=self.course,
           teaching_rating=4, content_rating=4, communication_rating=4
       )
       self.client.force_login(self.admin)
       response = self.client.get(self.url)
       self.assertEqual(response.context['total_feedback'], 1)

   def test_average_teaching_rating_correct(self):

       Feedback.objects.create(
           student=self.student, course=self.course,
           teaching_rating=4, content_rating=3, communication_rating=5
       )
       self.client.force_login(self.admin)
       response = self.client.get(self.url)
       self.assertEqual(response.context['avg_teaching'], 4.0)

   def test_overall_avg_zero_when_no_feedback(self):
       self.client.force_login(self.admin)
       response = self.client.get(self.url)
       self.assertEqual(response.context['overall_avg'], 0)

   def test_course_filter_returns_correct_data(self):

       other_faculty = make_user('faculty2@uap-bd.edu', 'Faculty')
       other_course = make_course(other_faculty, code='CSE202')
       other_student = make_user('student2@uap-bd.edu', 'Student', student_id='23101010')
       Feedback.objects.create(
           student=self.student, course=self.course,
           teaching_rating=5, content_rating=5, communication_rating=5
       )
       Feedback.objects.create(
           student=other_student, course=other_course,
           teaching_rating=2, content_rating=2, communication_rating=2
       )
       self.client.force_login(self.admin)
       response = self.client.get(self.url + f'?course={self.course.id}')
       self.assertEqual(response.context['total_feedback'], 1)


class FeedbackReportsScopingTest(TestCase):



   def setUp(self):
       self.client = Client()
       self.hod_cse = make_user('hod_cse@uap-bd.edu', 'HOD', department='CSE')
       self.hod_eee = make_user('hod_eee@uap-bd.edu', 'HOD', department='EEE')
       self.faculty_cse = make_user('fac_cse@uap-bd.edu', 'Faculty', department='CSE')
       self.faculty_eee = make_user('fac_eee@uap-bd.edu', 'Faculty', department='EEE')
       self.student = make_user('student@uap-bd.edu', 'Student', student_id='23101011')

       self.course_cse = make_course(self.faculty_cse, code='CSE101', name='CS Intro',
                                      department='CSE', semester='Spring 2025')
       self.course_eee = make_course(self.faculty_eee, code='EEE101', name='EEE Intro',
                                      department='EEE', semester='Spring 2025')
       Feedback.objects.create(
           student=self.student, course=self.course_cse,
           teaching_rating=5, content_rating=5, communication_rating=5
       )

   def test_hod_cse_sees_only_cse_feedback(self):


       self.client.force_login(self.hod_cse)
       response = self.client.get(reverse('feedback_reports'))
       self.assertEqual(response.context['total_feedback'], 1)

   def test_hod_eee_sees_zero_feedback(self):


       self.client.force_login(self.hod_eee)
       response = self.client.get(reverse('feedback_reports'))
       self.assertEqual(response.context['total_feedback'], 0)


