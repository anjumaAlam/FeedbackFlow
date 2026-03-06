from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import StudentRegistrationForm, LoginForm


def register_view(request):

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully")
            return redirect('login')

    else:
        form = StudentRegistrationForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):

    if request.method == 'POST':

        form = LoginForm(request.POST)

        if form.is_valid():

            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(request, username=email, password=password)

            if user:
                login(request, user)
                return redirect('student_dashboard')

            else:
                messages.error(request, "Invalid login")

    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def student_dashboard(request):
    return render(request, 'users/student_dashboard.html')