
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/login/', permanent=False), name='home'),
    path('', include('users.urls')),
    path('feedback/', include('feedback.urls')),
    path('complaints/', include('complaints.urls')),
]

admin.site.site_header = "FeedbackFlow Administration"
admin.site.site_title = "FeedbackFlow Admin Portal"
admin.site.index_title = "Welcome to FeedbackFlow Admin Panel"

