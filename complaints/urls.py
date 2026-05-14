# complaints/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ── Student ──────────────────────────────────────────────────────────
    path('submit/', views.submit_complaint, name='submit_complaint'),
    path('my-complaints/', views.my_complaints, name='my_complaints'),
    path('detail/<int:complaint_id>/', views.complaint_detail, name='complaint_detail'),

    # ── HOD ──────────────────────────────────────────────────────────────
    path('hod/list/', views.hod_complaints_list, name='hod_complaints_list'),
    path('hod/handle/<int:complaint_id>/', views.handle_complaint, name='handle_complaint'),
    path('hod/assign-investigation/<int:complaint_id>/', views.assign_investigation, name='assign_investigation'),
    path('hod/final-action/<int:complaint_id>/', views.hod_final_action, name='hod_final_action'),   # NEW

    # ── Investigator (Faculty) ────────────────────────────────────────────
    path('investigator/my-investigations/', views.investigator_dashboard, name='investigator_dashboard'),  # NEW
    path('investigator/submit-findings/<int:investigation_id>/', views.submit_findings, name='submit_findings'),  # NEW

    # ── Staff ─────────────────────────────────────────────────────────────
    path('staff/list/', views.staff_complaints_list, name='staff_complaints_list'),

    # ── Admin ─────────────────────────────────────────────────────────────
    path('admin/list/', views.admin_complaints_list, name='admin_complaints_list'),
    path('dao/list/', views.dao_complaints_list, name='dao_complaints_list'),
    path('dao/escalate/<int:complaint_id>/', views.dao_escalate_complaint, name='dao_escalate_complaint'),
    path('dao/assign-staff/<int:complaint_id>/', views.dao_assign_staff, name='dao_assign_staff'),
    path('staff/my-tasks/', views.staff_task_list, name='staff_task_list'),
    path('staff/mark-fixed/<int:complaint_id>/', views.staff_mark_fixed, name='staff_mark_fixed'),

    # ── NEW: FACULTY COMPLAINT ANALYSIS ──────────────────────────────────
    path('hod/faculty-complaint-summary/', views.faculty_complaint_summary, name='faculty_complaint_summary'),
    path('hod/faculty-course-wise/<int:faculty_id>/', views.faculty_course_wise_complaints, name='faculty_course_wise_complaints'),
    path('hod/similar-complaints/<int:faculty_id>/<int:group_index>/', views.similar_complaints_detail, name='similar_complaints_detail'),
    path('public-log/', views.public_log, name='public_log'),
]