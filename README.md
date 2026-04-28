# FeedbackFlow

Django app for collecting course feedback and managing course-to-faculty assignments (section-wise). Built for a university workflow with role-based access: Student, Faculty, HOD, Staff, Admin.

---

## Quick Features
- Custom `User` model with roles and departments.
- Students see department-scoped courses when submitting feedback.
- Section-wise faculty assignments (A/B/C/D) and primary assignment flag.
- Non-Django-admin admin pages to manage Courses and CourseAssignments.
- Feedback submission with server-side validation and anonymous option.

---

## Requirements
- Python 3.10+ (project tested with 3.10/3.11)
- See `requirements.txt` for Python packages

---

## Setup (local)
1. Create & activate virtualenv:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Unix / macOS
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Apply migrations and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
```

4. Run the dev server:

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/

---

## Important URLs
- Student feedback form: `/feedback/submit/`
- Admin dashboard: `/dashboard/admin/` (or login then navigate)
- Custom admin UI - Add Course: `/feedback/admin/courses/add/`
- Custom admin UI - Manage Assignments: `/feedback/admin/assignments/`
- Django admin (if needed): `/admin/`

---

## Data model notes
- `feedback.models.Course` stores course info and `department` (string). Departments use the `DEPARTMENT_CHOICES` in `users.models.User`.
- `feedback.models.CourseAssignment` links a `Course` to a faculty `User` and has `class_section` choices (`A`/`B`/`C`/`D`) and `is_primary`.
- `feedback.models.Feedback` links `student`, `course`, `faculty`, and stores ratings and optional comments. Students can submit only once per course (unique constraint) and are limited to department courses in the UI.

---

## Admin UI
Two custom admin pages were added so admins can manage courses and assignments without using Django admin:
- Course create page: `/feedback/admin/courses/add/`
- Assignments list/create: `/feedback/admin/assignments/` and `/feedback/admin/assignments/add/`

These pages require the logged-in user to have `role='Admin'`.

---

## Tests
Run Django tests:

```bash
python manage.py test
```

---

## Troubleshooting
- If the course dropdown is empty for a student, ensure:
  - Student `department` is set (see `users.User.department`).
  - There are `Course` entries whose `department` matches (code or display name).
- Use `python manage.py check` to surface common configuration issues.

---



