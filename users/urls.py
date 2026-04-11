

from django.urls import path
from . import views

urlpatterns = [

    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),


    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),


    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('faculty/dashboard/', views.faculty_dashboard, name='faculty_dashboard'),
    path('hod/dashboard/', views.hod_dashboard, name='hod_dashboard'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
]
