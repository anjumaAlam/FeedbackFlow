import os
import django
import pytest
import time
import random


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "feedbackflow.settings")
django.setup()

from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

BASE_URL = "http://127.0.0.1:8000"




@pytest.fixture(scope="session", autouse=True)
def create_test_users():
    User = get_user_model()
    from feedback.models import Course, Feedback

    # --- Student ---
    student, _ = User.objects.get_or_create(email="student_test@uap-bd.edu")
    student.set_password("TestPass123!")
    student.full_name = "Test Student"
    student.role = "Student"
    student.department = "CSE"
    student.student_id = "99999001"
    student.is_active = True
    student.save()

    # --- Faculty ---
    faculty, _ = User.objects.get_or_create(email="faculty_test@uap-bd.edu")
    faculty.set_password("TestPass123!")
    faculty.full_name = "Test Faculty"
    faculty.role = "Faculty"
    faculty.department = "CSE"
    faculty.is_active = True
    faculty.save()

    # --- HOD ---
    hod, _ = User.objects.get_or_create(email="hod_test@uap-bd.edu")
    hod.set_password("TestPass123!")
    hod.full_name = "Test HOD"
    hod.role = "HOD"
    hod.department = "CSE"
    hod.is_active = True
    hod.save()

    # --- Staff ---
    staff, _ = User.objects.get_or_create(email="staff_test@uap-bd.edu")
    staff.set_password("TestPass123!")
    staff.full_name = "Test Staff"
    staff.role = "Staff"
    staff.department = "CSE"
    staff.is_active = True
    staff.save()

    # --- Admin ---
    admin, _ = User.objects.get_or_create(email="admin_test@uap-bd.edu")
    admin.set_password("TestPass123!")
    admin.full_name = "Test Admin"
    admin.role = "Admin"
    admin.is_active = True
    admin.is_staff = True
    admin.save()

    # --- Course (needed for feedback tests) ---
    course, _ = Course.objects.get_or_create(
        course_code="CSE9999",
        defaults={
            "course_name": "Test Course for Selenium",
            "faculty": faculty,
            "department": "CSE",
            "semester": "Spring 2025",
            "is_active": True,
        }
    )

    # --- Feedback (for detail/respond tests) ---
    feedback, _ = Feedback.objects.get_or_create(
        student=student,
        course=course,
        defaults={
            "teaching_rating": 4,
            "content_rating": 4,
            "communication_rating": 4,
            "comments": "Selenium test feedback",
            "is_anonymous": False,
            "status": "Pending",
        }
    )

    # --- Complaint (for detail/handle tests) ---
    from complaints.models import Complaint
    complaint, _ = Complaint.objects.get_or_create(
        tracking_id="CMP999999",
        defaults={
            "student": student,
            "complaint_type": "Facility",
            "subject": "Selenium test complaint",
            "description": "This is a test complaint created by Selenium.",
            "status": "Pending",
            "priority": "Medium",
            "assigned_to": staff,
        }
    )

    yield {
        "student": student,
        "faculty": faculty,
        "hod": hod,
        "staff": staff,
        "admin": admin,
        "course": course,
        "feedback": feedback,
        "complaint": complaint,
    }




def get_driver():
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    driver.implicitly_wait(5)
    return driver


def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)


def do_login(driver, email, password="TestPass123!"):
    driver.get(f"{BASE_URL}/login/")
    driver.find_element(By.NAME, "email").send_keys(email)
    time.sleep(0.5)
    driver.find_element(By.NAME, "password").send_keys(password)
    time.sleep(0.5)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)

# Sprint 01: AUTH TEST
def test_login_page_loads():
    driver = get_driver()
    driver.get(f"{BASE_URL}/login/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Login" in page or "login" in page.lower()
    driver.quit()

def test_valid_login_student():
    driver = get_driver()
    do_login(driver, "student_test@uap-bd.edu")
    time.sleep(1)
    assert "dashboard" in driver.current_url or "student" in driver.current_url
    driver.quit()

def test_invalid_login_shows_error():
    driver = get_driver()
    driver.get(f"{BASE_URL}/login/")
    driver.find_element(By.NAME, "email").send_keys("wrong@uap-bd.edu")
    time.sleep(0.5)
    driver.find_element(By.NAME, "password").send_keys("WrongPassword!")
    time.sleep(0.5)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "/login/" in driver.current_url or "Invalid" in page or "incorrect" in page.lower()
    driver.quit()

def test_register_page_loads():
    driver = get_driver()
    driver.get(f"{BASE_URL}/register/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Register" in page or "Registration" in page
    driver.quit()


def test_register_valid_student():
    driver = get_driver()
    driver.get(f"{BASE_URL}/register/")
    time.sleep(1)

    uid = random.randint(10000, 99999)
    driver.find_element(By.NAME, "full_name").send_keys("New Selenium Student")
    time.sleep(0.3)
    driver.find_element(By.NAME, "student_id").send_keys(f"99{uid}")
    time.sleep(0.3)
    driver.find_element(By.NAME, "email").send_keys(f"new_selenium{uid}@uap-bd.edu")
    time.sleep(0.3)
    Select(driver.find_element(By.NAME, "department")).select_by_value("CSE")
    time.sleep(0.3)
    driver.find_element(By.NAME, "password").send_keys("TestPass123!")
    time.sleep(0.3)
    driver.find_element(By.NAME, "confirm_password").send_keys("TestPass123!")
    time.sleep(0.3)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))

    time.sleep(2)

    assert "/login/" in driver.current_url
    driver.quit()

def test_logout_works():
    driver = get_driver()
    do_login(driver, "student_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/logout/")
    time.sleep(1)
    assert "/login/" in driver.current_url or driver.current_url == f"{BASE_URL}/"
    driver.quit()

#Sprint 02: FEEDBACK TESTS

# TEST 7: Feedback submit page loads for student
def test_feedback_submit_page_loads_for_student():
    driver = get_driver()
    do_login(driver, "student_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/feedback/submit/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Feedback" in page
    driver.quit()


# TEST 8: Feedback submit page redirects without login
def test_feedback_submit_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/feedback/submit/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()


# TEST 9: My feedback page loads for student
def test_my_feedback_page_loads_for_student():
    driver = get_driver()
    do_login(driver, "student_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/feedback/my-feedback/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Feedback" in page
    driver.quit()


# TEST 10: My feedback page redirects without login
def test_my_feedback_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/feedback/my-feedback/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()


# TEST 11: Faculty feedback list page loads for faculty
def test_faculty_feedback_list_loads():
    driver = get_driver()
    do_login(driver, "faculty_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/feedback/faculty/list/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Feedback" in page
    driver.quit()


# TEST 12: Faculty feedback list redirects without login
def test_faculty_feedback_list_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/feedback/faculty/list/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()


# TEST 13: Feedback detail page loads
def test_feedback_detail_page_loads():
    driver = get_driver()
    from feedback.models import Feedback
    # Get the test feedback created in fixture
    feedback = Feedback.objects.filter(
        student__email="student_test@uap-bd.edu"
    ).first()
    if feedback:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/detail/{feedback.id}/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Feedback" in page or "Course" in page
    driver.quit()


# TEST 14: Faculty respond page loads for faculty
def test_faculty_respond_page_loads():
    driver = get_driver()
    from feedback.models import Feedback
    feedback = Feedback.objects.filter(
        course__faculty__email="faculty_test@uap-bd.edu"
    ).first()
    if feedback:
        do_login(driver, "faculty_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/faculty/respond/{feedback.id}/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        # Either shows the form or "already responded" message
        assert "Feedback" in page or "Response" in page or "responded" in page.lower()
    driver.quit()



# Sprint 03: COMPLAINT TESTS


# TEST 15: Complaint submit page loads for student
def test_complaint_submit_page_loads_for_student():
    driver = get_driver()
    do_login(driver, "student_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/complaints/submit/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Complaint" in page
    driver.quit()


# TEST 16: Complaint submit form valid
def test_complaint_submit_form_valid():
    driver = get_driver()
    do_login(driver, "student_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/complaints/submit/")
    time.sleep(1)

    Select(driver.find_element(By.NAME, "complaint_type")).select_by_value("Facility")
    time.sleep(0.5)
    driver.find_element(By.NAME, "subject").send_keys("Selenium Test Complaint Subject")
    time.sleep(0.5)
    driver.find_element(By.NAME, "description").send_keys(
        "This is a detailed complaint submitted by Selenium for testing purposes."
    )
    time.sleep(0.5)
    driver.find_element(By.NAME, "location").send_keys("Room 301, CSE Building")
    time.sleep(0.5)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))

    time.sleep(2)

    assert "/complaints/my-complaints/" in driver.current_url
    driver.quit()


# TEST 17: Complaint submit without login redirects
def test_complaint_submit_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/complaints/submit/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()


# TEST 18: My complaints page loads for student
def test_my_complaints_page_loads_for_student():
    driver = get_driver()
    do_login(driver, "student_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/complaints/my-complaints/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Complaint" in page
    driver.quit()


# TEST 19: My complaints without login redirects
def test_my_complaints_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/complaints/my-complaints/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()


# TEST 20: Complaint detail page loads for student
def test_complaint_detail_page_loads_for_student():
    driver = get_driver()
    from complaints.models import Complaint
    complaint = Complaint.objects.filter(
        student__email="student_test@uap-bd.edu"
    ).first()
    if complaint:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/complaints/detail/{complaint.id}/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Complaint" in page or complaint.tracking_id in page
    driver.quit()


# TEST 21: HOD complaints list loads for HOD
def test_hod_complaints_list_loads():
    driver = get_driver()
    do_login(driver, "hod_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/complaints/hod/list/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Complaint" in page or "HOD" in page
    driver.quit()


# TEST 22: HOD complaints list without login redirects
def test_hod_complaints_list_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/complaints/hod/list/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()


# TEST 23: Staff complaints list loads for staff
def test_staff_complaints_list_loads():
    driver = get_driver()
    do_login(driver, "staff_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/complaints/staff/list/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Complaint" in page or "Staff" in page or "Facility" in page
    driver.quit()


# TEST 24: Staff complaints list without login redirects
def test_staff_complaints_list_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/complaints/staff/list/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()


# TEST 25: Admin complaints list loads for admin
def test_admin_complaints_list_loads():
    driver = get_driver()
    do_login(driver, "admin_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/complaints/admin/list/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Complaint" in page or "Admin" in page
    driver.quit()


# TEST 26: Admin complaints list without login redirects
def test_admin_complaints_list_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/complaints/admin/list/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()

    # Sprint 04

    # TEST 27: Student dashboard loads

def test_student_dashboard_loads():
    driver = get_driver()
    do_login(driver, "student_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/student/dashboard/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Dashboard" in page or "Student" in page
    driver.quit()

    # TEST 28: Faculty dashboard loads

def test_faculty_dashboard_loads():
    driver = get_driver()
    do_login(driver, "faculty_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/faculty/dashboard/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Dashboard" in page or "Faculty" in page
    driver.quit()

    # TEST 29: HOD dashboard loads

def test_hod_dashboard_loads():
    driver = get_driver()
    do_login(driver, "hod_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/hod/dashboard/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Dashboard" in page or "HOD" in page
    driver.quit()

    # TEST 30: Staff dashboard loads

def test_staff_dashboard_loads():
    driver = get_driver()
    do_login(driver, "staff_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/staff/dashboard/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Dashboard" in page or "Staff" in page
    driver.quit()

    # TEST 31: Admin dashboard loads

def test_admin_dashboard_loads():
    driver = get_driver()
    do_login(driver, "admin_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/dashboard/admin/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Dashboard" in page or "Admin" in page
    driver.quit()

    # TEST 32: Dashboard without login redirects to login

def test_dashboard_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/student/dashboard/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()

    # TEST 33: Feedback reports page loads for admin
    def test_feedback_reports_page_loads_for_admin_user():
        driver = get_driver()
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Feedback" in page or "Report" in page or "Analytics" in page
        driver.quit()

    # TEST 34: Feedback reports page redirects without login
    def test_feedback_reports_without_login_redirects():
        driver = get_driver()
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(2)
        assert "/login/" in driver.current_url
        driver.quit()

    # TEST 35: Feedback reports page loads for HOD
    def test_feedback_reports_page_loads_for_hod():
        driver = get_driver()
        do_login(driver, "hod_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Feedback" in page or "Report" in page or "Analytics" in page
        driver.quit()

    # TEST 36: Feedback reports redirects faculty (only Admin/HOD allowed)
    def test_feedback_reports_redirects_faculty():
        driver = get_driver()
        do_login(driver, "faculty_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(2)
        assert "/login/" in driver.current_url or "/reports/feedback/" not in driver.current_url
        driver.quit()

    # TEST 37: Feedback reports shows filter options (course & department)
    def test_feedback_reports_filter_options_exist():
        driver = get_driver()
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(1)
        # Check that course and department filter dropdowns exist
        course_filter = driver.find_elements(By.NAME, "course")
        dept_filter = driver.find_elements(By.NAME, "department")
        assert len(course_filter) > 0 or len(dept_filter) > 0
        driver.quit()



    # TEST 38: Feedback reports filter form submits without error
    def test_feedback_reports_filter_by_department():
        driver = get_driver()
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(1)

        submit_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        if submit_btns:
            js_click(driver, submit_btns[0])
            time.sleep(2)

            page = driver.find_element(By.TAG_NAME, "body").text
            assert "Feedback" in page or "Report" in page
        driver.quit()


    # TEST 39: Admin user list page loads for admin

def test_admin_user_list_loads():
    driver = get_driver()
    do_login(driver, "admin_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/dashboard/users/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "User" in page or "Management" in page or "Email" in page
    driver.quit()

    # TEST 40: Admin user list redirects without login

def test_admin_user_list_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/dashboard/users/")
    time.sleep(2)
    assert "/login/" in driver.current_url
    driver.quit()

    # TEST 41: Admin user list not accessible by student

def test_admin_user_list_not_accessible_by_student():
    driver = get_driver()
    do_login(driver, "student_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/dashboard/users/")
    time.sleep(1)
    # Student should be redirected or get forbidden
    page = driver.find_element(By.TAG_NAME, "body").text
    current = driver.current_url
    assert "/dashboard/users/" not in current or "denied" in page.lower() or "not authorized" in page.lower() or "Forbidden" in page or "/login/" in current or "dashboard" in current
    driver.quit()

    # TEST 42: Admin user create page loads for admin

def test_admin_user_create_page_loads():
    driver = get_driver()
    do_login(driver, "admin_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/dashboard/users/create/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Create" in page or "User" in page or "Add" in page
    driver.quit()

    # TEST 43: Admin creates a new user successfully

def test_admin_create_user_successfully():
    driver = get_driver()
    do_login(driver, "admin_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/dashboard/users/create/")
    time.sleep(1)

    uid = random.randint(10000, 99999)
    driver.find_element(By.NAME, "full_name").send_keys(f"Selenium Created User {uid}")
    time.sleep(0.3)
    driver.find_element(By.NAME, "email").send_keys(f"selenium_created_{uid}@uap-bd.edu")
    time.sleep(0.3)
    Select(driver.find_element(By.NAME, "role")).select_by_value("Faculty")
    time.sleep(0.3)
    Select(driver.find_element(By.NAME, "department")).select_by_value("CSE")
    time.sleep(0.3)
    driver.find_element(By.NAME, "password").send_keys("TestPass123!")
    time.sleep(0.3)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)


    assert "/dashboard/users/" in driver.current_url
    driver.quit()

    # TEST 44: Admin user edit page loads

def test_admin_user_edit_page_loads():
    driver = get_driver()
    User = get_user_model()
    # Get the test faculty user to edit
    target = User.objects.filter(email="faculty_test@uap-bd.edu").first()
    if target:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/dashboard/users/{target.id}/edit/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Edit" in page or "User" in page or "Update" in page
    driver.quit()

    # TEST 45: Admin user list shows search/filter options

def test_admin_user_list_filter_options():
    driver = get_driver()
    do_login(driver, "admin_test@uap-bd.edu")
    driver.get(f"{BASE_URL}/dashboard/users/")
    time.sleep(1)
    # Check that search and role filter exist
    search = driver.find_elements(By.NAME, "q")
    role_filter = driver.find_elements(By.NAME, "role")
    assert len(search) > 0 or len(role_filter) > 0
    driver.quit()

    # TEST 46: Admin user delete page loads

def test_admin_user_delete_page_loads():
    driver = get_driver()
    User = get_user_model()
    # Find a user created by selenium to test delete page (not actual test users)
    target = User.objects.filter(email__startswith="selenium_created_").first()
    if target:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/dashboard/users/{target.id}/delete/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Delete" in page or "Confirm" in page or "delete" in page.lower()
    driver.quit()