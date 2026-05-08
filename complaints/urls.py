# complaints/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('submit/', views.submit_complaint, name='submit_complaint'),
    path('my-complaints/', views.my_complaints, name='my_complaints'),
    path('detail/<int:complaint_id>/', views.complaint_detail, name='complaint_detail'),

    path('hod/list/', views.hod_complaints_list, name='hod_complaints_list'),
    path('hod/handle/<int:complaint_id>/', views.handle_complaint, name='handle_complaint'),

    # NEW: Assign investigators from the handle page
    path('hod/assign-investigation/<int:complaint_id>/', views.assign_investigation, name='assign_investigation'),

    path('staff/list/', views.staff_complaints_list, name='staff_complaints_list'),

    path('admin/list/', views.admin_complaints_list, name='admin_complaints_list'),
]