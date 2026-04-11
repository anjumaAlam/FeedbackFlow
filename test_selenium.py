import os
import django
import pytest
import time


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


