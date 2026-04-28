
from django.urls import path
from . import views

urlpatterns = [
    # Home page
    path('', views.home_view, name='home'),
    
    # Registration
    path('register/', views.register_view, name='register'),
    
    # Role-based logins
    path('login/', views.student_login_view, name='login'),
    path('login/student/', views.student_login_view, name='student_login'),
    path('login/faculty/', views.faculty_login_view, name='faculty_login'),
    path('login/staff/', views.staff_login_view, name='staff_login'),
    path('login/admin/', views.admin_login_view, name='admin_login'),
    
    # Logout
    path('logout/', views.logout_view, name='logout'),


    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),


    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('faculty/dashboard/', views.faculty_dashboard, name='faculty_dashboard'),
    path('hod/dashboard/', views.hod_dashboard, name='hod_dashboard'),
    path('hod/faculty/', views.hod_faculty_list, name='hod_faculty_list'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),




    path('dashboard/users/', views.admin_user_list, name='admin_user_list'),
    path('dashboard/users/create/', views.admin_user_create, name='admin_user_create'),
    path('dashboard/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('dashboard/users/<int:user_id>/delete/', views.admin_user_delete, name='admin_user_delete'),
    path('dashboard/users/<int:user_id>/toggle-active/', views.admin_user_toggle_active, name='admin_user_toggle_active'),

    path('dashboard/feedback-reports/', views.feedback_reports, name='feedback_reports'),
    path('reports/feedback/', views.feedback_reports, name='feedback_reports_alt'),
    path('appointment/', views.appointment_view, name='appointment'),
]

