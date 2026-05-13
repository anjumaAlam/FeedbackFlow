from django.urls import path
from . import views

urlpatterns = [
    # ── Home ─────────────────────────────────────────────────────────────
    path('', views.home_view, name='home'),

    # ── Registration ─────────────────────────────────────────────────────
    path('register/', views.register_view, name='register'),

    # ── Unified login (one page for ALL roles) ────────────────────────────
    path('login/', views.unified_login_view, name='login'),

    # ── Individual role logins (kept for backward compatibility) ──────────
    path('login/student/',    views.student_login_view,   name='student_login'),
    path('login/faculty/',    views.faculty_login_view,   name='faculty_login'),
    path('login/staff/',      views.staff_login_view,     name='staff_login'),
    path('login/admin/',      views.admin_login_view,     name='admin_login'),
    path('login/committee/',  views.committee_login_view, name='committee_login'),
    path('login/dao/',        views.dao_login_view,       name='dao_login'),

    # ── Logout ────────────────────────────────────────────────────────────
    path('logout/', views.logout_view, name='logout'),

    # ── Password reset ────────────────────────────────────────────────────
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),

    # ── Dashboards ────────────────────────────────────────────────────────
    path('student/dashboard/',   views.student_dashboard,   name='student_dashboard'),
    path('faculty/dashboard/',   views.faculty_dashboard,   name='faculty_dashboard'),
    path('hod/dashboard/',       views.hod_dashboard,       name='hod_dashboard'),
    path('hod/faculty/',         views.hod_faculty_list,    name='hod_faculty_list'),
    path('staff/dashboard/',     views.staff_dashboard,     name='staff_dashboard'),
    path('dashboard/admin/',     views.admin_dashboard,     name='admin_dashboard'),
    path('committee/dashboard/', views.committee_dashboard, name='committee_dashboard'),
    path('dao/dashboard/',       views.dao_dashboard,       name='dao_dashboard'),

    # ── Admin user management ─────────────────────────────────────────────
    path('dashboard/users/',                              views.admin_user_list,         name='admin_user_list'),
    path('dashboard/users/create/',                       views.admin_user_create,        name='admin_user_create'),
    path('dashboard/users/<int:user_id>/edit/',           views.admin_user_edit,          name='admin_user_edit'),
    path('dashboard/users/<int:user_id>/delete/',         views.admin_user_delete,        name='admin_user_delete'),
    path('dashboard/users/<int:user_id>/toggle-active/',  views.admin_user_toggle_active, name='admin_user_toggle_active'),

    # ── Reports ───────────────────────────────────────────────────────────
    path('dashboard/feedback-reports/', views.feedback_reports, name='feedback_reports'),
    path('reports/feedback/',           views.feedback_reports, name='feedback_reports_alt'),
    path('dashboard/feedback-analytics/', views.feedback_analytics, name='feedback_analytics'),

    # ── Appointments ──────────────────────────────────────────────────────
    path('appointment/',                                   views.appointment_view,             name='appointment'),
    path('appointment/my/',                                views.my_appointments,              name='my_appointments'),
    path('dashboard/appointments/',                        views.admin_appointments,           name='admin_appointments'),
    path('dashboard/appointments/<int:appointment_id>/',   views.admin_appointment_detail,     name='admin_appointment_detail'),
    path('committee/appointment/<int:appointment_id>/',    views.committee_appointment_action, name='committee_appointment_action'),

    # ── Notifications ─────────────────────────────────────────────────────
    path('notifications/',                            views.notifications_view,     name='notifications'),
    path('notifications/mark-read/<int:notif_id>/',   views.mark_notification_read, name='mark_notification_read'),

    # ── Tasks ─────────────────────────────────────────────────────────────
    path('tasks/',                       views.task_list,   name='task_list'),
    path('tasks/add/',                   views.task_add,    name='task_add'),
    path('tasks/<int:task_id>/toggle/',  views.task_toggle, name='task_toggle'),
    path('tasks/<int:task_id>/delete/',  views.task_delete, name='task_delete'),
]

