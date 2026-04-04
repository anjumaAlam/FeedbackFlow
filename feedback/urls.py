

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
]