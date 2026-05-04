

from django.urls import path
from . import views

urlpatterns = [
    # Student URLs
    path('submit/', views.submit_feedback, name='submit_feedback'),
    path('my-feedback/', views.my_feedback, name='my_feedback'),
    path('detail/<int:feedback_id>/', views.feedback_detail, name='feedback_detail'),

    # Faculty URLs
    path('faculty/list/', views.faculty_feedback_list, name='faculty_feedback_list'),
    path('faculty/respond/<int:feedback_id>/', views.respond_to_feedback, name='respond_to_feedback'),
    path('faculty/mark-reviewed/<int:feedback_id>/', views.mark_feedback_reviewed, name='mark_feedback_reviewed'),
    # Admin UI for managing assignments (non-Django-admin)
    path('admin/courses/add/', views.course_create, name='admin_course_add'),
    path('admin/courses/', views.admin_course_list, name='admin_course_list'),
    path('admin/courses/<int:course_id>/delete/', views.admin_course_delete, name='admin_course_delete'),
    path('admin/assignments/', views.assignment_list, name='admin_assignments'),
    path('admin/assignments/add/', views.assignment_create, name='admin_assignment_add'),
    path('course-registration/', views.course_registration_view, name='course_registration'),
]