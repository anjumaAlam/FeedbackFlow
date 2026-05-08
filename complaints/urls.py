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
]