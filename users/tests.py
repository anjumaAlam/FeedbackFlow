from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest import skip
from feedback.models import Course, Feedback
from complaints.models import Complaint

User = get_user_model()


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ORIGINAL TESTS (Authentication Module)                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class UserModelTest(TestCase):
    """Test the custom User model"""

    def setUp(self):
        """Create a test user"""
        self.user = User.objects.create_user(
            email='student@uap-bd.edu',
            password='Student@123',
            full_name='Test Student',
            role='Student',
            student_id='23101157',
            department='CSE'
        )

    def test_user_creation(self):
        """Test that user is created successfully"""
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.user.email, 'student@uap-bd.edu')
        self.assertEqual(self.user.full_name, 'Test Student')
        self.assertEqual(self.user.role, 'Student')

    def test_user_email_is_unique(self):
        """Test that email must be unique"""
        self.assertTrue(User.objects.filter(email='student@uap-bd.edu').exists())

    def test_password_is_hashed(self):
        """Test that password is not stored in plain text"""
        self.assertNotEqual(self.user.password, 'Student@123')
        self.assertTrue(self.user.check_password('Student@123'))

    def test_user_string_representation(self):
        """Test the __str__ method"""
        expected = "Test Student (student@uap-bd.edu)"
        self.assertEqual(str(self.user), expected)

    def test_get_short_name(self):
        """Test getting user's first name"""
        self.assertEqual(self.user.get_short_name(), 'Test')

    def test_user_is_active_by_default(self):
        """Test that new users are active by default"""
        self.assertTrue(self.user.is_active)

    def test_user_is_not_staff_by_default(self):
        """Test that regular users are not staff"""
        self.assertFalse(self.user.is_staff)

    def test_student_has_student_id(self):
        """Test that student has student ID"""
        self.assertEqual(self.user.student_id, '23101157')

    def test_user_has_department(self):
        """Test that user has department"""
        self.assertEqual(self.user.department, 'CSE')


class RegistrationViewTest(TestCase):
    """Test the registration view"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()
        self.register_url = reverse('register')

    def test_registration_page_exists(self):
        """Test that registration page loads"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)

    def test_registration_uses_correct_template(self):
        """Test that correct template is used"""
        response = self.client.get(self.register_url)
        self.assertTemplateUsed(response, 'users/register.html')

    def test_registration_page_contains_form(self):
        """Test that registration page has a form"""
        response = self.client.get(self.register_url)
        self.assertContains(response, '<form')
        self.assertContains(response, 'email')
        self.assertContains(response, 'password')

    def test_successful_registration_creates_user(self):
        """Test that valid registration creates a user"""
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
        """Test that successful registration redirects to login"""
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
        """Test that registration assigns Student role"""
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
    """Test the login view"""

    def setUp(self):
        """Set up test client and user"""
        self.client = Client()
        self.login_url = reverse('login')
        self.user = User.objects.create_user(
            email='student@uap-bd.edu',
            password='Student@123',
            full_name='Test Student',
            role='Student'
        )

    def test_login_page_exists(self):
        """Test that login page loads"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_login_uses_correct_template(self):
        """Test that correct template is used"""
        response = self.client.get(self.login_url)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_login_page_contains_form(self):
        """Test that login page has a form"""
        response = self.client.get(self.login_url)
        self.assertContains(response, '<form')
        self.assertContains(response, 'email')
        self.assertContains(response, 'password')

    def test_successful_login_redirects(self):
        """Test that successful login redirects"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        self.assertEqual(response.status_code, 302)

    def test_successful_login_authenticates_user(self):
        """Test that successful login authenticates the user"""
        self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'Student@123'
        })
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_wrong_password_does_not_login(self):
        """Test that wrong password fails"""
        response = self.client.post(self.login_url, {
            'email': 'student@uap-bd.edu',
            'password': 'WrongPassword@123'
        })
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_user_cannot_login(self):
        """Test that non-existent user cannot login"""
        response = self.client.post(self.login_url, {
            'email': 'nonexistent@uap-bd.edu',
            'password': 'Test@123'
        })
        self.assertEqual(response.status_code, 200)


class LogoutViewTest(TestCase):
    """Test the logout view"""

    def setUp(self):
        """Set up test client and user"""
        self.client = Client()
        self.logout_url = reverse('logout')
        self.user = User.objects.create_user(
            email='student@uap-bd.edu',
            password='Student@123',
            full_name='Test Student',
            role='Student'
        )

    def test_logout_redirects_to_login(self):
        """Test that logout redirects to login page"""
        self.client.login(username='student@uap-bd.edu', password='Student@123')
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)

    def test_logout_clears_session(self):
        """Test that logout clears the session"""
        self.client.login(username='student@uap-bd.edu', password='Student@123')
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.client.get(self.logout_url)
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 302)


class PasswordResetTest(TestCase):
    """Test password reset functionality"""

    def setUp(self):
        """Set up test client and user"""
        self.client = Client()
        self.reset_url = reverse('password_reset_request')
        self.user = User.objects.create_user(
            email='student@uap-bd.edu',
            password='Student@123',
            full_name='Test Student',
            role='Student'
        )

    def test_password_reset_page_exists(self):
        """Test that password reset page loads"""
        response = self.client.get(self.reset_url)
        self.assertEqual(response.status_code, 200)

    def test_password_reset_uses_correct_template(self):
        """Test that correct template is used"""
        response = self.client.get(self.reset_url)
        self.assertTemplateUsed(response, 'users/password_reset_request.html')

    def test_password_reset_page_contains_form(self):
        """Test that password reset page has form"""
        response = self.client.get(self.reset_url)
        self.assertContains(response, '<form')
        self.assertContains(response, 'email')


class DashboardAccessTest(TestCase):
    """Test dashboard access control"""

    def setUp(self):
        """Set up test users"""
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
        """Test that student can access their dashboard"""
        self.client.login(username='student@uap-bd.edu', password='Student@123')
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_faculty_can_access_faculty_dashboard(self):
        """Test that faculty can access their dashboard"""
        self.client.login(username='faculty@uap-bd.edu', password='Faculty@123')
        response = self.client.get(reverse('faculty_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_cannot_access_dashboard(self):
        """Test that unauthenticated user is redirected"""
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_student_dashboard_shows_user_info(self):
        """Test that dashboard displays user information"""
        self.client.login(username='student@uap-bd.edu', password='Student@123')
        response = self.client.get(reverse('student_dashboard'))
        self.assertContains(response, 'Test Student')
        self.assertContains(response, 'student@uap-bd.edu')


class URLTest(TestCase):
    """Test that all URLs are accessible"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()

    def test_login_url_exists(self):
        """Test login URL exists"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_register_url_exists(self):
        """Test register URL exists"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_password_reset_url_exists(self):
        """Test password reset URL exists"""
        response = self.client.get(reverse('password_reset_request'))
        self.assertEqual(response.status_code, 200)

    def test_root_url_redirects_to_login(self):
        """Test that root URL redirects to login"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)


class FormTest(TestCase):
    """Test form validation (basic)"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()
        self.register_url = reverse('register')

    def test_registration_form_accepts_valid_data(self):
        """Test that form accepts valid data"""
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
        """Test that all required fields must be filled"""
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


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ADMIN USER MANAGEMENT                                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# ── PART 1: User Model (role, active/inactive) ────────────────────────────

class UserModelRoleTest(TestCase):
    """Admin User Management | User model role & field validation"""

    def test_all_roles_can_be_created(self):
        """Student/Faculty/HOD/Staff/Admin সব role valid"""
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
        """is_active=False সেট করে save করলে user deactivate হয়"""
        u = User.objects.create_user(
            email='todeactivate@uap-bd.edu', password='Test@1234',
            full_name='To Deactivate', role='Faculty'
        )
        u.is_active = False
        u.save()
        u.refresh_from_db()
        self.assertFalse(u.is_active)

    def test_deactivated_user_cannot_login(self):
        """Inactive user login করতে পারবে না"""
        User.objects.create_user(
            email='inactive@uap-bd.edu', password='Test@1234',
            full_name='Inactive User', role='Faculty', is_active=False
        )
        c = Client()
        c.post(reverse('login'), {'email': 'inactive@uap-bd.edu', 'password': 'Test@1234'})
        response = c.get(reverse('faculty_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_admin_superuser_has_is_staff_true(self):
        """create_superuser দিয়ে বানালে is_staff=True হয়"""
        admin = User.objects.create_superuser(
            email='superadmin@uap-bd.edu', password='Admin@1234'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_duplicate_email_raises_error(self):
        """একই email দিয়ে দুইটা user বানানো যাবে না"""
        User.objects.create_user(
            email='dup@uap-bd.edu', password='Test@1234',
            full_name='First', role='Faculty'
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='dup@uap-bd.edu', password='Test@1234',
                full_name='Second', role='Staff'
            )


# ── PART 2: Admin Dashboard View ─────────────────────────────────────────

class AdminDashboardViewTest(TestCase):
    """Admin User Management | admin_dashboard view"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='admin@uap-bd.edu', password='Test@1234',
            full_name='Test Admin', role='Admin'
        )
        self.student = User.objects.create_user(
            email='student@uap-bd.edu', password='Test@1234',
            full_name='Test Student', role='Student', student_id='23101002'
        )
        self.url = reverse('admin_dashboard')

    def test_unauthenticated_user_redirected(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_admin_can_access_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_dashboard_shows_correct_total_users(self):
        """setUp-এ 2 user আছে, total_users=2 হবে"""
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_users'], 2)

    def test_dashboard_shows_student_count(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.context['student_count'], 1)

    def test_dashboard_uses_correct_template(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'users/admin_dashboard.html')


# ── PART 3: Admin-only Access Validation ─────────────────────────────────

class AdminOnlyAccessTest(TestCase):
    """Admin User Management | শুধু Admin admin dashboard-এ যেতে পারবে"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='admin@uap-bd.edu', password='Test@1234',
            full_name='Admin', role='Admin'
        )
        User.objects.create_user(
            email='student@uap-bd.edu', password='Test@1234',
            full_name='Student', role='Student', student_id='23101003'
        )
        User.objects.create_user(
            email='faculty@uap-bd.edu', password='Test@1234',
            full_name='Faculty', role='Faculty'
        )
        User.objects.create_user(
            email='hod@uap-bd.edu', password='Test@1234',
            full_name='HOD', role='HOD'
        )
        User.objects.create_user(
            email='staff@uap-bd.edu', password='Test@1234',
            full_name='Staff', role='Staff'
        )
        self.url = reverse('admin_dashboard')

    def test_student_blocked(self):
        self.client.login(username='student@uap-bd.edu', password='Test@1234')
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_faculty_blocked(self):
        self.client.login(username='faculty@uap-bd.edu', password='Test@1234')
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_hod_blocked(self):
        self.client.login(username='hod@uap-bd.edu', password='Test@1234')
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_staff_blocked(self):
        self.client.login(username='staff@uap-bd.edu', password='Test@1234')
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_only_admin_gets_200(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)


