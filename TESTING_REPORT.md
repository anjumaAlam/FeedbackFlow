# FeedbackFlow Authentication Module

## Testing Report

**Project:** FeedbackFlow - Student Feedback Management System
**Module:** Authentication System
**Institution:** University of Asia Pacific
**Department:** Computer Science & Engineering

**Submitted by:**
Anjuma Alam
Student ID: [Your Student ID]
Email: [Your Email]

**Date:** March 7, 2026

---

# Executive Summary

This document presents the unit testing results for the Authentication module of the FeedbackFlow system. The tests were conducted using Django’s built-in testing framework. A total of **37 unit tests** were executed covering different parts of the authentication system including user models, registration, login, logout, password reset, dashboard access, form validation, and URL routing.

All tests were successfully executed with a **100% pass rate**, confirming that the authentication system functions correctly and meets the expected requirements.

---

# 1. Introduction

## 1.1 Purpose

The purpose of this testing report is to document the unit testing performed on the Authentication module of the FeedbackFlow system. Testing ensures that the system behaves as expected and that all authentication features work correctly.

---

## 1.2 Scope

The following components were tested:

* Custom User Model
* Student Registration System
* User Login
* User Logout
* Password Reset Page
* Role-based Dashboard Access
* URL Routing
* Form Validation

---

## 1.3 Testing Environment

| Component        | Description          |
| ---------------- | -------------------- |
| Framework        | Django               |
| Language         | Python               |
| Database         | SQLite Test Database |
| Testing Tool     | Django TestCase      |
| IDE              | PyCharm              |
| Operating System | Windows              |

---

# 2. Test Results Summary

## 2.1 Overall Statistics

| Metric         | Value           |
| -------------- | --------------- |
| Total Tests    | 37              |
| Passed         | 37              |
| Failed         | 0               |
| Skipped        | 0               |
| Success Rate   | 100%            |
| Execution Time | 147.034 seconds |

---

## 2.2 Test Categories

| Category               | Description                               | Status |
| ---------------------- | ----------------------------------------- | ------ |
| User Model Tests       | Tests for custom user model functionality | Pass   |
| Registration Tests     | Tests for student registration            | Pass   |
| Login Tests            | Tests for login functionality             | Pass   |
| Logout Tests           | Tests for logout functionality            | Pass   |
| Password Reset Tests   | Tests for password reset page             | Pass   |
| Dashboard Access Tests | Tests for role-based dashboard access     | Pass   |
| URL Routing Tests      | Tests for correct URL configuration       | Pass   |
| Form Validation Tests  | Tests for form input validation           | Pass   |

---

# 3. Detailed Test Cases

## 3.1 User Model Tests

**Test Class:** `UserModelTest`

These tests verify that the custom user model functions correctly.

Test cases included:

* User creation
* Email uniqueness validation
* Password hashing verification
* Default user status
* Student ID validation
* Department assignment
* User string representation
* Staff permissions validation
* Short name retrieval

All tests passed successfully.

---

## 3.2 Registration Tests

**Test Class:** `RegistrationViewTest`

These tests verify that the registration system works properly.

Test cases included:

* Registration page loads successfully
* Registration page contains form
* Correct template is used
* Successful registration creates a user
* Registration assigns student role
* Successful registration redirects to login page

All tests passed successfully.

---

## 3.3 Login Tests

**Test Class:** `LoginViewTest`

These tests verify login functionality.

Test cases included:

* Login page exists
* Login page contains form
* Correct template used
* Successful login authentication
* Successful login redirect
* Wrong password rejection
* Non-existent user login rejection

All tests passed successfully.

---

## 3.4 Logout Tests

**Test Class:** `LogoutViewTest`

These tests verify logout functionality.

Test cases included:

* Logout clears session
* Logout redirects to login page

All tests passed successfully.

---

## 3.5 Password Reset Tests

**Test Class:** `PasswordResetTest`

These tests verify password reset page behavior.

Test cases included:

* Password reset page exists
* Page contains reset form
* Correct template used

All tests passed successfully.

---

## 3.6 Dashboard Access Tests

**Test Class:** `DashboardAccessTest`

These tests verify role-based dashboard access.

Test cases included:

* Student can access student dashboard
* Faculty can access faculty dashboard
* Dashboard displays user information
* Unauthenticated user redirected to login

All tests passed successfully.

---

## 3.7 URL Routing Tests

**Test Class:** `URLTest`

These tests verify correct URL routing.

Test cases included:

* Login URL exists
* Register URL exists
* Password reset URL exists
* Root URL redirects to login

All tests passed successfully.

---

# 4. Test Execution Evidence

The tests were executed using the following command:

```
python manage.py test users --verbosity=2

```
## Test Execution Screenshot

Below is the screenshot of the terminal after running the Django unit tests.

![Unit Test Result](screenshots/unit_test.png)

### Sample Terminal Output

```
Found 37 test(s).
Creating test database for alias 'default'...
System check identified no issues.

----------------------------------------------------------------------
Ran 37 tests in 147.034s

OK
Destroying test database for alias 'default'...
```

This confirms that all tests ran successfully without any errors.

---

# 5. Defects Found

No defects were found during testing.
All **37 tests passed successfully**.

---

# 6. Recommendations

Future improvements may include:

* Adding integration tests for email notifications
* Testing password strength validation
* Adding performance testing
* Adding security testing for authentication

---

# 7. Conclusion

The Authentication module of the FeedbackFlow system was successfully tested using Django’s testing framework.

The testing confirmed that:

* User registration works correctly
* Login authentication is secure
* Passwords are properly hashed
* Role-based dashboard access works
* URL routing functions correctly
* Form validation is properly implemented

All **37 tests passed successfully**, indicating that the authentication system is stable and ready for integration with other modules of the system.

---

# Appendix

## Test File Location

```
users/tests.py
```

---

## Command Used to Run Tests

```
python manage.py test users
```

---

**Prepared by:**
Anjuma Alam

**Date:** March 7, 2026
