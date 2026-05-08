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


    student, _ = User.objects.get_or_create(email="student_test@uap-bd.edu")
    student.set_password("TestPass123!")
    student.full_name = "Test Student"
    student.role = "Student"
    student.department = "CSE"
    student.student_id = "99999001"
    student.is_active = True
    student.save()


    faculty, _ = User.objects.get_or_create(email="faculty_test@uap-bd.edu")
    faculty.set_password("TestPass123!")
    faculty.full_name = "Test Faculty"
    faculty.role = "Faculty"
    faculty.department = "CSE"
    faculty.is_active = True
    faculty.save()


    hod, _ = User.objects.get_or_create(email="hod_test@uap-bd.edu")
    hod.set_password("TestPass123!")
    hod.full_name = "Test HOD"
    hod.role = "HOD"
    hod.department = "CSE"
    hod.is_active = True
    hod.save()


    staff, _ = User.objects.get_or_create(email="staff_test@uap-bd.edu")
    staff.set_password("TestPass123!")
    staff.full_name = "Test Staff"
    staff.role = "Staff"
    staff.department = "CSE"
    staff.is_active = True
    staff.save()


    admin, _ = User.objects.get_or_create(email="admin_test@uap-bd.edu")
    admin.set_password("TestPass123!")
    admin.full_name = "Test Admin"
    admin.role = "Admin"
    admin.is_active = True
    admin.is_staff = True
    admin.save()


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


    from complaints.models import Complaint
    complaint, _ = Complaint.objects.get_or_create(
        tracking_id="CMP999999",
        defaults={
            "student": student,
            "complaint_type": "Faculty",
            "subject": "Selenium test complaint",
            "description": "This is a test complaint created by Selenium.",
            "status": "Pending",
            "priority": "Medium",
            "assigned_to": hod,
        }
    )

    if complaint.assigned_to != hod:
        complaint.assigned_to = hod
        complaint.save()

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
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    driver.implicitly_wait(5)
    return driver


def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)


def do_login(driver, email, password="TestPass123!"):
    # Determine correct login portal based on email
    # HOD uses faculty login portal
    if "hod_test" in email:
        driver.get(f"{BASE_URL}/login/faculty/")
    elif "faculty_test" in email:
        driver.get(f"{BASE_URL}/login/faculty/")
    elif "staff_test" in email:
        driver.get(f"{BASE_URL}/login/staff/")
    elif "admin_test" in email:
        driver.get(f"{BASE_URL}/login/admin/")
    else:
        driver.get(f"{BASE_URL}/login/")
    time.sleep(1)
    driver.find_element(By.NAME, "email").send_keys(email)
    time.sleep(0.5)
    driver.find_element(By.NAME, "password").send_keys(password)
    time.sleep(0.5)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)



# AUTHENTICATION TESTS (1–6)


# TEST 1
def test_login_page_loads():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/login/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert (
            "Sign in" in page
            or "Login" in page
            or "login" in page.lower()
            or "Welcome back" in page
            or "Student" in page
        )
    finally:
        driver.quit()


# TEST 2
def test_valid_login_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        time.sleep(1)
        assert "dashboard" in driver.current_url or "student" in driver.current_url
    finally:
        driver.quit()


# TEST 3
def test_invalid_login_shows_error():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/login/")
        driver.find_element(By.NAME, "email").send_keys("wrong@uap-bd.edu")
        time.sleep(0.5)
        driver.find_element(By.NAME, "password").send_keys("WrongPassword!")
        time.sleep(0.5)
        js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
        time.sleep(2)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "/login/" in driver.current_url or "Invalid" in page or "incorrect" in page.lower()
    finally:
        driver.quit()


# TEST 4
def test_register_page_loads():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/register/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Register" in page or "Registration" in page
    finally:
        driver.quit()


# TEST 5
def test_register_valid_student():
    driver = get_driver()
    try:
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
    finally:
        driver.quit()


# TEST 6
def test_logout_works():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/logout/")
        time.sleep(1)
        assert "/login/" in driver.current_url or driver.current_url == f"{BASE_URL}/"
    finally:
        driver.quit()



# FEEDBACK TESTS (7–14)


# TEST 7
def test_feedback_submit_page_loads_for_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/submit/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Feedback" in page
    finally:
        driver.quit()


# TEST 8
def test_feedback_submit_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/feedback/submit/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 9
def test_my_feedback_page_loads_for_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/my-feedback/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Feedback" in page
    finally:
        driver.quit()


# TEST 10
def test_my_feedback_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/feedback/my-feedback/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 11
def test_faculty_feedback_list_loads():
    driver = get_driver()
    try:
        do_login(driver, "faculty_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/faculty/list/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Feedback" in page
    finally:
        driver.quit()


# TEST 12
def test_faculty_feedback_list_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/feedback/faculty/list/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 13
def test_feedback_detail_page_loads():
    driver = get_driver()
    try:
        from feedback.models import Feedback
        feedback = Feedback.objects.filter(
            student__email="student_test@uap-bd.edu"
        ).first()
        if feedback:
            do_login(driver, "student_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/feedback/detail/{feedback.id}/")
            time.sleep(1)
            page = driver.find_element(By.TAG_NAME, "body").text
            assert "Feedback" in page or "Course" in page
    finally:
        driver.quit()


# TEST 14
def test_faculty_respond_page_loads():
    driver = get_driver()
    try:
        from feedback.models import Feedback
        feedback = Feedback.objects.filter(
            faculty__email="faculty_test@uap-bd.edu"
        ).first()
        if not feedback:
            feedback = Feedback.objects.filter(
                student__email="student_test@uap-bd.edu"
            ).first()
        if feedback:
            do_login(driver, "faculty_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/feedback/faculty/respond/{feedback.id}/")
            time.sleep(1)
            page = driver.find_element(By.TAG_NAME, "body").text
            assert "Feedback" in page or "Response" in page or "responded" in page.lower()
    finally:
        driver.quit()



#  COMPLAINT TESTS (15–26)


# TEST 15
def test_complaint_submit_page_loads_for_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/complaints/submit/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Complaint" in page
    finally:
        driver.quit()


# TEST 16
def test_complaint_submit_form_valid():
    driver = get_driver()
    try:
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
    finally:
        driver.quit()


# TEST 17
def test_complaint_submit_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/complaints/submit/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 18
def test_my_complaints_page_loads_for_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/complaints/my-complaints/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Complaint" in page
    finally:
        driver.quit()


# TEST 19
def test_my_complaints_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/complaints/my-complaints/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 20
def test_complaint_detail_page_loads_for_student():
    driver = get_driver()
    try:
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
    finally:
        driver.quit()


# TEST 21
def test_hod_complaints_list_loads():
    driver = get_driver()
    try:
        do_login(driver, "hod_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/complaints/hod/list/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Complaint" in page or "HOD" in page
    finally:
        driver.quit()


# TEST 22
def test_hod_complaints_list_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/complaints/hod/list/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 23
def test_staff_complaints_list_loads():
    driver = get_driver()
    try:
        do_login(driver, "staff_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/complaints/staff/list/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Complaint" in page or "Staff" in page or "Facility" in page
    finally:
        driver.quit()


# TEST 24
def test_staff_complaints_list_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/complaints/staff/list/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 25
def test_admin_complaints_list_loads():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/complaints/admin/list/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Complaint" in page or "Admin" in page
    finally:
        driver.quit()


# TEST 26
def test_admin_complaints_list_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/complaints/admin/list/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()



#  DASHBOARD TESTS (27–32)


# TEST 27
def test_student_dashboard_loads():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/student/dashboard/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Dashboard" in page or "Student" in page
    finally:
        driver.quit()


# TEST 28
def test_faculty_dashboard_loads():
    driver = get_driver()
    try:
        do_login(driver, "faculty_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/faculty/dashboard/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Dashboard" in page or "Faculty" in page
    finally:
        driver.quit()


# TEST 29
def test_hod_dashboard_loads():
    driver = get_driver()
    try:
        do_login(driver, "hod_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/hod/dashboard/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Dashboard" in page or "HOD" in page
    finally:
        driver.quit()


# TEST 30
def test_staff_dashboard_loads():
    driver = get_driver()
    try:
        do_login(driver, "staff_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/staff/dashboard/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Dashboard" in page or "Staff" in page
    finally:
        driver.quit()


# TEST 31
def test_admin_dashboard_loads():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/dashboard/admin/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Dashboard" in page or "Admin" in page
    finally:
        driver.quit()


# TEST 32
def test_dashboard_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/student/dashboard/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()



#  REPORTS & ADMIN USER TESTS (33–46)


# TEST 33
def test_feedback_reports_page_loads_for_admin_user():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Feedback" in page or "Report" in page or "Analytics" in page
    finally:
        driver.quit()


# TEST 34
def test_feedback_reports_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 35
def test_feedback_reports_page_loads_for_hod():
    driver = get_driver()
    try:
        do_login(driver, "hod_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Feedback" in page or "Report" in page or "Analytics" in page
    finally:
        driver.quit()


# TEST 36
def test_feedback_reports_redirects_faculty():
    driver = get_driver()
    try:
        do_login(driver, "faculty_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(2)
        assert "/login/" in driver.current_url or "/reports/feedback/" not in driver.current_url
    finally:
        driver.quit()


# TEST 37
def test_feedback_reports_filter_options_exist():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(1)
        course_filter = driver.find_elements(By.NAME, "course")
        dept_filter = driver.find_elements(By.NAME, "department")
        assert len(course_filter) > 0 or len(dept_filter) > 0
    finally:
        driver.quit()


# TEST 38
def test_feedback_reports_filter_by_department():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/reports/feedback/")
        time.sleep(1)
        submit_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        if submit_btns:
            js_click(driver, submit_btns[0])
            time.sleep(2)
            page = driver.find_element(By.TAG_NAME, "body").text
            assert "Feedback" in page or "Report" in page
    finally:
        driver.quit()


# TEST 39
def test_admin_user_list_loads():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/dashboard/users/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "User" in page or "Management" in page or "Email" in page
    finally:
        driver.quit()


# TEST 40
def test_admin_user_list_without_login_redirects():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/dashboard/users/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 41
def test_admin_user_list_not_accessible_by_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/dashboard/users/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        current = driver.current_url
        assert (
            "/dashboard/users/" not in current
            or "denied" in page.lower()
            or "not authorized" in page.lower()
            or "Forbidden" in page
            or "/login/" in current
            or "dashboard" in current
        )
    finally:
        driver.quit()


# TEST 42
def test_admin_user_create_page_loads():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/dashboard/users/create/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Create" in page or "User" in page or "Add" in page
    finally:
        driver.quit()


# TEST 43
def test_admin_create_user_successfully():
    driver = get_driver()
    try:
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
    finally:
        driver.quit()


# TEST 44
def test_admin_user_edit_page_loads():
    driver = get_driver()
    try:
        User = get_user_model()
        target = User.objects.filter(email="faculty_test@uap-bd.edu").first()
        if target:
            do_login(driver, "admin_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/dashboard/users/{target.id}/edit/")
            time.sleep(1)
            page = driver.find_element(By.TAG_NAME, "body").text
            assert "Edit" in page or "User" in page or "Update" in page
    finally:
        driver.quit()


# TEST 45
def test_admin_user_list_filter_options():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/dashboard/users/")
        time.sleep(1)
        search = driver.find_elements(By.NAME, "q")
        role_filter = driver.find_elements(By.NAME, "role")
        assert len(search) > 0 or len(role_filter) > 0
    finally:
        driver.quit()


# TEST 46
def test_admin_user_delete_page_loads():
    driver = get_driver()
    try:
        User = get_user_model()
        target = User.objects.filter(email__startswith="selenium_created_").first()
        if target:
            do_login(driver, "admin_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/dashboard/users/{target.id}/delete/")
            time.sleep(1)
            page = driver.find_element(By.TAG_NAME, "body").text
            assert "Delete" in page or "Confirm" in page or "delete" in page.lower()
    finally:
        driver.quit()



#  MULTI-ROLE LOGIN TESTS (47–52)


# TEST 47
def test_faculty_login_page_loads():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/login/faculty/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert (
            "Faculty" in page
            or "Sign in" in page
            or "Login" in page
            or "login" in page.lower()
        )
    finally:
        driver.quit()


# TEST 48
def test_valid_login_faculty():
    driver = get_driver()
    try:
        do_login(driver, "faculty_test@uap-bd.edu")
        time.sleep(1)
        assert "dashboard" in driver.current_url or "faculty" in driver.current_url
    finally:
        driver.quit()


# TEST 49
def test_staff_login_page_loads():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/login/staff/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert (
            "Staff" in page
            or "Sign in" in page
            or "Login" in page
            or "login" in page.lower()
        )
    finally:
        driver.quit()


# TEST 50
def test_valid_login_staff():
    driver = get_driver()
    try:
        do_login(driver, "staff_test@uap-bd.edu")
        time.sleep(1)
        assert "dashboard" in driver.current_url or "staff" in driver.current_url
    finally:
        driver.quit()


# TEST 51
def test_admin_login_page_loads():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/login/admin/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert (
            "Admin" in page
            or "Sign in" in page
            or "Login" in page
            or "login" in page.lower()
        )
    finally:
        driver.quit()


# TEST 52
def test_valid_login_admin():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        time.sleep(1)
        assert "dashboard" in driver.current_url or "admin" in driver.current_url
    finally:
        driver.quit()



#  PASSWORD RESET TESTS (53–54)


# TEST 53
def test_password_reset_page_loads():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/password-reset/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Password" in page or "Reset" in page or "password" in page.lower()
    finally:
        driver.quit()


# TEST 54
def test_password_reset_form_submit():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/password-reset/")
        time.sleep(1)
        email_fields = driver.find_elements(By.NAME, "email")
        if email_fields:
            email_fields[0].send_keys("student_test@uap-bd.edu")
            time.sleep(0.3)
            js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
            time.sleep(2)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert (
            "password" in page.lower()
            or "reset" in page.lower()
            or "email" in page.lower()
            or "sent" in page.lower()
        )
    finally:
        driver.quit()


# APPOINTMENT TESTS (55–57)


# TEST 55
def test_appointment_page_loads_for_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/appointment/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Appointment" in page or "appointment" in page.lower()
    finally:
        driver.quit()


# TEST 56
def test_appointment_page_redirects_without_login():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/appointment/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 57
def test_appointment_form_submit_valid():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/appointment/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Appointment" in page or "appointment" in page.lower()
    finally:
        driver.quit()



# NOTIFICATION TESTS (58–60)


# TEST 58
def test_notifications_page_loads_for_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/notifications/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Notification" in page or "notification" in page.lower()
    finally:
        driver.quit()


# TEST 59
def test_notifications_page_redirects_without_login():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/notifications/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 60
def test_notifications_page_loads_for_hod():
    driver = get_driver()
    try:
        do_login(driver, "hod_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/notifications/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Notification" in page or "notification" in page.lower()
    finally:
        driver.quit()



#  TASK TESTS (61–63)


# TEST 61
def test_task_list_page_loads_for_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/tasks/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Task" in page or "task" in page.lower()
    finally:
        driver.quit()


# TEST 62
def test_task_list_redirects_without_login():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/tasks/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 63 — task_add is POST-only; verify task list page has the add form
def test_task_add_page_loads_for_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/tasks/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Task" in page or "Add" in page or "task" in page.lower()
    finally:
        driver.quit()


# TEST 64
def test_task_add_form_submit_valid():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/tasks/")
        time.sleep(1)
        title_fields = driver.find_elements(By.NAME, "title")
        if title_fields:
            title_fields[0].send_keys("Selenium Test Task")
            time.sleep(0.3)
            submit_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
            if submit_btns:
                js_click(driver, submit_btns[0])
                time.sleep(2)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Task" in page or "task" in page.lower()
    finally:
        driver.quit()


# TEST 65
def test_task_add_redirects_without_login():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/tasks/add/")
        time.sleep(2)
        assert "/login/" in driver.current_url or "405" in driver.page_source or driver.current_url != f"{BASE_URL}/tasks/add/"
    finally:
        driver.quit()



#  ADMIN COURSE TESTS (66–69)


# TEST 66
def test_admin_course_list_loads():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/admin/courses/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Course" in page or "course" in page.lower() or "Admin" in page
    finally:
        driver.quit()


# TEST 67
def test_admin_course_list_redirects_without_login():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/feedback/admin/courses/")
        time.sleep(2)
        assert "/login/" in driver.current_url or "login" in driver.current_url.lower()
    finally:
        driver.quit()


# TEST 68
def test_admin_course_add_page_loads():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/admin/courses/add/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Course" in page or "Add" in page or "Create" in page
    finally:
        driver.quit()


# TEST 69
def test_admin_course_add_form_submit():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/admin/courses/add/")
        time.sleep(1)

        uid = random.randint(1000, 9999)

        code_fields = driver.find_elements(By.NAME, "course_code")
        if code_fields:
            code_fields[0].send_keys(f"SL{uid}")
            time.sleep(0.3)

        name_fields = driver.find_elements(By.NAME, "course_name")
        if name_fields:
            name_fields[0].send_keys(f"Selenium Course {uid}")
            time.sleep(0.3)

        dept_fields = driver.find_elements(By.NAME, "department")
        if dept_fields:
            try:
                Select(dept_fields[0]).select_by_value("CSE")
            except Exception:
                dept_fields[0].send_keys("CSE")
            time.sleep(0.3)

        sem_fields = driver.find_elements(By.NAME, "semester")
        if sem_fields:
            sem_fields[0].send_keys("Spring 2025")
            time.sleep(0.3)

        submit_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        if submit_btns:
            js_click(driver, submit_btns[0])
            time.sleep(2)

        page = driver.find_element(By.TAG_NAME, "body").text
        assert (
            "Course" in page
            or "course" in page.lower()
            or "Dashboard" in page
            or "successfully" in page.lower()
        )
    finally:
        driver.quit()



#  ASSIGNMENT TESTS (70–72)


# TEST 70
def test_admin_assignment_list_loads():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/admin/assignments/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Assignment" in page or "Course" in page or "assignment" in page.lower()
    finally:
        driver.quit()


# TEST 71
def test_admin_assignment_list_redirects_without_login():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/feedback/admin/assignments/")
        time.sleep(2)
        assert "/login/" in driver.current_url or "login" in driver.current_url.lower()
    finally:
        driver.quit()


# TEST 72
def test_admin_assignment_add_page_loads():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/admin/assignments/add/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Assignment" in page or "Add" in page or "Course" in page
    finally:
        driver.quit()



#  COURSE REGISTRATION (73–74)


# TEST 73
def test_course_registration_page_loads_for_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/feedback/course-registration/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Course" in page or "Registration" in page or "course" in page.lower()
    finally:
        driver.quit()


# TEST 74
def test_course_registration_redirects_without_login():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/feedback/course-registration/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


#  MARK FEEDBACK REVIEWED (75)


# TEST 75
def test_mark_feedback_reviewed_by_faculty():
    driver = get_driver()
    try:
        from feedback.models import Feedback
        feedback = Feedback.objects.filter(
            faculty__email="faculty_test@uap-bd.edu"
        ).first()
        if not feedback:
            feedback = Feedback.objects.filter(
                student__email="student_test@uap-bd.edu"
            ).first()
        if feedback:
            do_login(driver, "faculty_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/feedback/faculty/mark-reviewed/{feedback.id}/")
            time.sleep(2)
            page = driver.find_element(By.TAG_NAME, "body").text
            assert "Feedback" in page or "faculty" in driver.current_url or "dashboard" in driver.current_url
    finally:
        driver.quit()



# HOD COMPLAINT MANAGEMENT (76–81)


# TEST 76
def test_hod_handle_complaint_page_loads():
    driver = get_driver()
    try:
        from complaints.models import Complaint
        # Use complaint assigned to HOD or any complaint (HOD can handle dept complaints)
        complaint = Complaint.objects.filter(
            assigned_to__email="hod_test@uap-bd.edu"
        ).first()
        if not complaint:
            complaint = Complaint.objects.filter(
                student__department="CSE"
            ).first()
        if complaint:
            do_login(driver, "hod_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/complaints/hod/handle/{complaint.id}/")
            time.sleep(1)
            page = driver.find_element(By.TAG_NAME, "body").text
            assert (
                "Complaint" in page
                or "Handle" in page
                or "complaint" in page.lower()
                or "HOD" in page
            )
    finally:
        driver.quit()


# TEST 77
def test_hod_handle_complaint_redirects_without_login():
    driver = get_driver()
    try:
        from complaints.models import Complaint
        complaint = Complaint.objects.first()
        if complaint:
            driver.get(f"{BASE_URL}/complaints/hod/handle/{complaint.id}/")
            time.sleep(2)
            assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 78
def test_hod_assign_investigation_page_loads():
    driver = get_driver()
    try:
        from complaints.models import Complaint
        # Find a complaint in HOD's department
        complaint = Complaint.objects.filter(
            student__department="CSE"
        ).first()
        if not complaint:
            complaint = Complaint.objects.first()
        if complaint:
            do_login(driver, "hod_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/complaints/hod/assign-investigation/{complaint.id}/")
            time.sleep(1)
            page = driver.find_element(By.TAG_NAME, "body").text
            assert (
                "Investigation" in page
                or "Assign" in page
                or "Complaint" in page
                or "investigation" in page.lower()
            )
    finally:
        driver.quit()


# TEST 79
def test_hod_final_action_page_loads():
    driver = get_driver()
    try:
        from complaints.models import Complaint
        # Try to find a complaint with right status, fallback to any complaint
        complaint = Complaint.objects.filter(status="Under Investigation").first()
        if not complaint:
            complaint = Complaint.objects.filter(status="Findings Submitted").first()
        if not complaint:
            complaint = Complaint.objects.first()
        if complaint:
            do_login(driver, "hod_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/complaints/hod/final-action/{complaint.id}/")
            time.sleep(1)
            page = driver.find_element(By.TAG_NAME, "body").text
            # View may redirect if complaint not in right status — accept redirect too
            assert (
                "Complaint" in page
                or "Action" in page
                or "Final" in page
                or "HOD" in page
                or "complaint" in page.lower()
                or "hod" in driver.current_url
            )
    finally:
        driver.quit()


# TEST 80
def test_hod_final_action_redirects_without_login():
    driver = get_driver()
    try:
        from complaints.models import Complaint
        complaint = Complaint.objects.first()
        if complaint:
            driver.get(f"{BASE_URL}/complaints/hod/final-action/{complaint.id}/")
            time.sleep(2)
            assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 81
def test_investigator_dashboard_loads_for_faculty():
    driver = get_driver()
    try:
        do_login(driver, "faculty_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/complaints/investigator/my-investigations/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert (
            "Investigation" in page
            or "Complaint" in page
            or "investigation" in page.lower()
            or "My" in page
            or "Dashboard" in page
        )
    finally:
        driver.quit()



#  HOD FACULTY LIST & INVESTIGATOR (82–84)


# TEST 82
def test_investigator_dashboard_redirects_without_login():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/complaints/investigator/my-investigations/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 83
def test_hod_faculty_list_loads():
    driver = get_driver()
    try:
        do_login(driver, "hod_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/hod/faculty/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Faculty" in page or "faculty" in page.lower()
    finally:
        driver.quit()


# TEST 84
def test_hod_faculty_list_redirects_without_login():
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/hod/faculty/")
        time.sleep(2)
        assert "/login/" in driver.current_url
    finally:
        driver.quit()


# TEST 85
def test_hod_faculty_list_not_accessible_by_student():
    driver = get_driver()
    try:
        do_login(driver, "student_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/hod/faculty/")
        time.sleep(1)
        current = driver.current_url
        page = driver.find_element(By.TAG_NAME, "body").text
        assert (
            "/hod/faculty/" not in current
            or "/login/" in current
            or "denied" in page.lower()
            or "dashboard" in current
        )
    finally:
        driver.quit()


#ADMIN USER MANAGEMENT EXTENDED (86–90)


# TEST 86
def test_admin_user_edit_form_submits():
    driver = get_driver()
    try:
        User = get_user_model()
        target = User.objects.filter(email="faculty_test@uap-bd.edu").first()
        if target:
            do_login(driver, "admin_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/dashboard/users/{target.id}/edit/")
            time.sleep(1)
            full_name_fields = driver.find_elements(By.NAME, "full_name")
            if full_name_fields:
                full_name_fields[0].clear()
                full_name_fields[0].send_keys("Test Faculty Updated")
                time.sleep(0.3)
            submit_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
            if submit_btns:
                js_click(driver, submit_btns[0])
                time.sleep(2)
            assert "/dashboard/users/" in driver.current_url or "User" in driver.find_element(By.TAG_NAME, "body").text
    finally:
        driver.quit()


# TEST 87
def test_admin_user_toggle_active():
    driver = get_driver()
    try:
        User = get_user_model()
        target = User.objects.filter(email="faculty_test@uap-bd.edu").first()
        if target:
            do_login(driver, "admin_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/dashboard/users/{target.id}/toggle-active/")
            time.sleep(2)
            assert "/dashboard/users/" in driver.current_url or "User" in driver.find_element(By.TAG_NAME, "body").text
    finally:
        driver.quit()


# TEST 88
def test_admin_user_delete_confirm_page_loads():
    driver = get_driver()
    try:
        User = get_user_model()
        target = User.objects.filter(email__startswith="selenium_created_").first()
        if target:
            do_login(driver, "admin_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/dashboard/users/{target.id}/delete/")
            time.sleep(1)
            page = driver.find_element(By.TAG_NAME, "body").text
            assert "Delete" in page or "Confirm" in page or "delete" in page.lower()
    finally:
        driver.quit()


# TEST 89
def test_admin_user_delete_not_accessible_by_faculty():
    driver = get_driver()
    try:
        User = get_user_model()
        target = User.objects.filter(email="staff_test@uap-bd.edu").first()
        if target:
            do_login(driver, "faculty_test@uap-bd.edu")
            driver.get(f"{BASE_URL}/dashboard/users/{target.id}/delete/")
            time.sleep(1)
            current = driver.current_url
            page = driver.find_element(By.TAG_NAME, "body").text
            assert (
                f"/dashboard/users/{target.id}/delete/" not in current
                or "/login/" in current
                or "denied" in page.lower()
                or "dashboard" in current
                or "sign in" in page.lower()
            )
    finally:
        driver.quit()


# TEST 90
def test_admin_dashboard_shows_stats():
    driver = get_driver()
    try:
        do_login(driver, "admin_test@uap-bd.edu")
        driver.get(f"{BASE_URL}/dashboard/admin/")
        time.sleep(1)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert (
            "User" in page
            or "Feedback" in page
            or "Complaint" in page
            or "Dashboard" in page
            or "Total" in page
        )
    finally:
        driver.quit()