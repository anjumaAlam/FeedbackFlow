import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedbackflow.settings')
django.setup()

from complaints.models import Complaint
from users.models import User

# Get any student to be the creator
student = User.objects.filter(role='Student').first()

if student:
    # 1. Broken AC
    Complaint.objects.create(
        student=student,
        complaint_type='Facility',
        subject='Broken AC in Room 402',
        description='The air conditioner in Room 402 was making a loud noise and dripping water. It has been repaired.',
        location='Room 402, Building B',
        status='Resolved',
        resolved_at=timezone.now() - timedelta(days=1)
    )

    # 2. Slow Wi-Fi
    Complaint.objects.create(
        student=student,
        complaint_type='Facility',
        subject='Slow Wi-Fi in the Library',
        description='The router on the 3rd floor of the library was malfunctioning. The IT department has replaced the router.',
        location='Central Library, 3rd Floor',
        status='Resolved',
        resolved_at=timezone.now() - timedelta(days=3)
    )

    # 3. Projector issue
    Complaint.objects.create(
        student=student,
        complaint_type='Facility',
        subject='Projector bulb burnt out',
        description='The projector in CSE Seminar Room was not turning on. The maintenance team replaced the bulb.',
        location='CSE Seminar Room',
        status='Resolved',
        resolved_at=timezone.now() - timedelta(days=5)
    )

    print("Successfully added 3 resolved facility complaints to the database!")
else:
    print("Error: Could not find any Student user in the database to assign the complaints to.")
