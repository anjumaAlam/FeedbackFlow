"""
Auto Feedback Generator for FeedbackFlow
=========================================
Run with:  venv\Scripts\python manage.py shell -c "exec(open('auto_feedback.py').read())"
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedbackflow.settings')

import random
from datetime import datetime, timedelta
from django.utils import timezone
from users.models import User
from feedback.models import Course, CourseAssignment, Feedback

print("=" * 60)
print("GENERATING FEEDBACK DATA FOR ANALYTICS CHARTS")
print("=" * 60)

students = list(User.objects.filter(role='Student', is_active=True))
courses  = list(Course.objects.filter(is_active=True))

if not students:
    print("\n ERROR: No students found! Run auto_create.txt first.")
    sys.exit(1)
if not courses:
    print("\n ERROR: No courses found! Run auto_course.txt first.")
    sys.exit(1)

print(f"\n  Found {len(students)} students")
print(f"  Found {len(courses)} courses")
print(f"  Existing feedback in DB: {Feedback.objects.count()}")

created  = 0
skipped  = 0
errors   = 0

positive = [
    "Excellent teaching! Very well explained.",
    "The lectures were very engaging and informative.",
    "Great course content, learned a lot.",
    "The faculty was very helpful and supportive.",
    "One of the best courses at UAP.",
    "Very interactive classes with practical examples.",
    "Clear explanations and well-structured syllabus.",
    "The professor is very knowledgeable.",
    "Really enjoyed the hands-on projects.",
    "Good balance between theory and practical.",
]
neutral = [
    "Decent course overall, could use more examples.",
    "The course was okay, but assignments were too many.",
    "Average experience. Some topics were rushed.",
    "Teaching was adequate but could be more interactive.",
    "Content was good but pacing needs improvement.",
    "Reasonable course, met my expectations.",
    "Some lectures were good, others felt repetitive.",
    "Not bad, would benefit from better materials.",
]
negative = [
    "The lectures were hard to follow at times.",
    "Too much theory, not enough practical application.",
    "Communication could be improved significantly.",
    "Pace was too fast, hard to keep up.",
    "Needs more office hours and student support.",
]

sections = ['A', 'B', 'C', 'D']
weights  = [5, 10, 20, 35, 30]

now = timezone.now()
date_ranges = []
for mb in range(5, -1, -1):
    ms = (now - timedelta(days=mb * 30)).replace(day=1, hour=9, minute=0, second=0, microsecond=0)
    date_ranges.append(ms)

print(f"\n  Generating across {len(date_ranges)} months:")
for d in date_ranges:
    print(f"    - {d.strftime('%B %Y')}")
print("\n  Creating feedback entries...\n")

for student in students:
    dept_courses = [c for c in courses if c.department == student.department]
    if not dept_courses:
        continue
    num = min(len(dept_courses), random.randint(2, 4))
    selected = random.sample(dept_courses, num)
    for course in selected:
        if Feedback.objects.filter(student=student, course=course).exists():
            skipped += 1
            continue
        assignment = CourseAssignment.objects.filter(course=course).first()
        faculty = assignment.faculty if assignment else None
        section = random.choice(sections)
        tr = random.choices([1,2,3,4,5], weights=weights, k=1)[0]
        cr = random.choices([1,2,3,4,5], weights=weights, k=1)[0]
        comr = random.choices([1,2,3,4,5], weights=weights, k=1)[0]
        avg = (tr + cr + comr) / 3
        comment = random.choice(positive if avg >= 4 else (neutral if avg >= 2.5 else negative))
        anon = random.random() < 0.2
        status = random.choices(['Pending','Reviewed','Responded'], weights=[30,40,30], k=1)[0]
        base = random.choice(date_ranges)
        sub_at = base + timedelta(days=random.randint(0,28), hours=random.randint(8,20), minutes=random.randint(0,59))
        try:
            fb = Feedback(student=student, course=course, faculty=faculty, teaching_rating=tr, content_rating=cr, communication_rating=comr, comments=comment, class_section=section, is_anonymous=anon, status=status)
            fb.save()
            Feedback.objects.filter(id=fb.id).update(submitted_at=sub_at)
            if status in ['Reviewed','Responded']:
                Feedback.objects.filter(id=fb.id).update(reviewed_at=sub_at + timedelta(days=random.randint(1,7)))
            created += 1
            if created % 20 == 0:
                print(f"    Created {created} feedback entries...")
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"    Error: {student.email} -> {course.course_code}: {e}")

total_in_db = Feedback.objects.count()
print("\n" + "=" * 60)
print("FEEDBACK GENERATION COMPLETE!")
print("=" * 60)
print(f"\n  Created this run : {created}")
print(f"  Skipped (exists) : {skipped}")
print(f"  Errors           : {errors}")
print(f"  Total in DB      : {total_in_db}")

print("\n  RATING DISTRIBUTION (Teaching):")
for star in range(1, 6):
    cnt = Feedback.objects.filter(teaching_rating=star).count()
    pct = (cnt / total_in_db * 100) if total_in_db else 0
    print(f"    {star} Star : {cnt:3d}  ({pct:5.1f}%)")

print("\n  FEEDBACK BY DEPARTMENT:")
for dc, dn in User.DEPARTMENT_CHOICES:
    cnt = Feedback.objects.filter(course__department=dc).count()
    print(f"    {dc:15s}: {cnt:3d}")

print("\n  MONTHLY TREND:")
for d in date_ranges:
    nm = (d + timedelta(days=32)).replace(day=1)
    cnt = Feedback.objects.filter(submitted_at__gte=d, submitted_at__lt=nm).count()
    print(f"    {d.strftime('%B %Y'):15s}: {cnt:3d}")

print("\n" + "=" * 60)
print("  NOW GO TO: /dashboard/feedback-analytics/")
print("  LOGIN AS:  admin@uap-bd.edu / Admin@123")
print("=" * 60)
