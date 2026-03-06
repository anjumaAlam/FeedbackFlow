# feedbackflow/urls.py

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [

    path('admin/', admin.site.urls),

    path('', RedirectView.as_view(url='/login/', permanent=False)),

    path('', include('users.urls')),
]

# Customize admin site
admin.site.site_header = "FeedbackFlow Administration"
admin.site.site_title = "FeedbackFlow Admin"
admin.site.index_title = "Welcome to FeedbackFlow Admin Panel"