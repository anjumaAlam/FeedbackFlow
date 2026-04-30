from django.shortcuts import render, redirect

def homepage_view(request):
    if request.user.is_authenticated:
        role_redirects = {
            'Student': 'student_dashboard',
            'Faculty': 'faculty_dashboard',
            'HOD': 'hod_dashboard',
            'Staff': 'staff_dashboard',
            'Admin': 'admin_dashboard',
        }
        return redirect(role_redirects.get(request.user.role, 'login'))

    context = {
        'page_title': 'Welcome to FeedbackFlow'
    }
    return render(request, 'homepage/index.html', context)