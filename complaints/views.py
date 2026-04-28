

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count

from .models import Complaint, ComplaintUpdate
from .forms import ComplaintSubmissionForm, ComplaintUpdateForm
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe
from users.models import User
import json




@login_required
def submit_complaint(request):
    """Student submits a complaint"""

    if request.user.role != 'Student':
        messages.error(request, 'Only students can submit complaints.')
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = ComplaintSubmissionForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.student = request.user
            complaint.save()

            messages.success(
                request,
                f'Complaint submitted successfully! Tracking ID: {complaint.tracking_id}'
            )
            return redirect('my_complaints')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ComplaintSubmissionForm()
    # Build users-by-role mapping for frontend filtering
    roles = ['Faculty', 'HOD', 'Staff']
    users_by_role = {}
    for r in roles:
        qs = User.objects.filter(role=r, is_active=True).order_by('full_name')
        users_by_role[r] = [{'id': u.id, 'name': u.full_name} for u in qs]

    context = {
        'form': form,
        'page_title': 'Submit Complaint',
        'users_by_role': users_by_role,
    }
    return render(request, 'complaints/submit_complaints.html', context)


@login_required
def my_complaints(request):
    """Student views their submitted complaints"""

    if request.user.role != 'Student':
        messages.error(request, 'Access denied.')
        return redirect('login')

    complaints_list = Complaint.objects.filter(student=request.user).order_by('-submitted_at')


    total_complaints = complaints_list.count()
    pending = complaints_list.filter(status='Pending').count()
    resolved = complaints_list.filter(status='Resolved').count()

    context = {
        'complaints_list': complaints_list,
        'total_complaints': total_complaints,
        'pending': pending,
        'resolved': resolved,
        'page_title': 'My Complaints'
    }
    return render(request, 'complaints/my_complaints.html', context)


@login_required
def complaint_detail(request, complaint_id):
    """View detailed complaint with updates"""

    complaint = get_object_or_404(Complaint, id=complaint_id)


    if request.user.role == 'Student' and complaint.student != request.user:
        messages.error(request, 'You can only view your own complaints.')
        return redirect('my_complaints')


    updates = complaint.updates.all().order_by('created_at')

    context = {
        'complaint': complaint,
        'updates': updates,
        'page_title': f'Complaint {complaint.tracking_id}'
    }
    return render(request, 'complaints/complaint_detail.html', context)




@login_required


def hod_complaints_list(request):
    """HOD views complaints assigned to them (faculty complaints)"""

    if request.user.role != 'HOD':
        messages.error(request, 'Access denied. HOD only.')
        return redirect('login')

    from django.db.models import Q
    complaints_list = Complaint.objects.filter(
        Q(assigned_to=request.user) |
        Q(faculty_concerned__department=request.user.department)
    ).distinct().order_by('-submitted_at')

    total_complaints = complaints_list.count()
    pending = complaints_list.filter(status='Pending').count()
    investigating = complaints_list.filter(status='Under Investigation').count()
    resolved = complaints_list.filter(status='Resolved').count()
    escalated = complaints_list.filter(status='Escalated').count()

    context = {
        'complaints_list': complaints_list,
        'total_complaints': total_complaints,
        'pending': pending,
        'investigating': investigating,
        'resolved': resolved,
        'escalated': escalated,
        'page_title': 'Faculty Complaints'
    }
    return render(request, 'complaints/hod_complaints_list.html', context)


@login_required
def handle_complaint(request, complaint_id):
    """HOD/Staff/Admin handles a complaint"""

    if request.user.role not in ['HOD', 'Staff', 'Admin']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    complaint = get_object_or_404(Complaint, id=complaint_id)

    if request.user.role == 'HOD':
        if complaint.assigned_to != request.user and \
                (complaint.faculty_concerned is None or
                 complaint.faculty_concerned.department != request.user.department):
            messages.error(request, 'This complaint is not assigned to you.')
            return redirect('hod_complaints_list')
    elif request.user.role != 'Admin':
        if complaint.assigned_to != request.user:
            messages.error(request, 'This complaint is not assigned to you.')
            return redirect('login')

    if request.method == 'POST':
        form = ComplaintUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.complaint = complaint
            update.updated_by = request.user
            update.save()


            if update.status_changed_to:
                complaint.status = update.status_changed_to


                if update.status_changed_to == 'Resolved':
                    complaint.resolved_at = timezone.now()

                complaint.save()

            messages.success(request, 'Complaint updated successfully!')


            if request.user.role == 'HOD':
                return redirect('hod_complaints_list')
            elif request.user.role == 'Staff':
                return redirect('staff_complaints_list')
            else:  # Admin
                return redirect('admin_complaints_list')
    else:
        form = ComplaintUpdateForm()


    updates = complaint.updates.all().order_by('created_at')

    context = {
        'form': form,
        'complaint': complaint,
        'updates': updates,
        'page_title': f'Handle Complaint {complaint.tracking_id}'
    }
    return render(request, 'complaints/handle_complaint.html', context)




@login_required
def staff_complaints_list(request):
    """Staff views facility complaints assigned to them"""

    if request.user.role != 'Staff':
        messages.error(request, 'Access denied. Staff only.')
        return redirect('login')


    complaints_list = Complaint.objects.filter(
        assigned_to=request.user
    ).order_by('-submitted_at')


    total_complaints = complaints_list.count()
    pending = complaints_list.filter(status='Pending').count()
    investigating = complaints_list.filter(status='Under Investigation').count()
    resolved = complaints_list.filter(status='Resolved').count()

    context = {
        'complaints_list': complaints_list,
        'total_complaints': total_complaints,
        'pending': pending,
        'investigating': investigating,
        'resolved': resolved,
        'page_title': 'Facility Complaints'
    }
    return render(request, 'complaints/staff_complaints_list.html', context)




@login_required
def admin_complaints_list(request):
    """Admin views all complaints or complaints assigned to them"""

    if request.user.role != 'Admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('login')


    complaints_list = Complaint.objects.all().order_by('-submitted_at')


    total_complaints = complaints_list.count()
    pending = complaints_list.filter(status='Pending').count()
    investigating = complaints_list.filter(status='Under Investigation').count()
    resolved = complaints_list.filter(status='Resolved').count()
    escalated = complaints_list.filter(status='Escalated').count()


    faculty_complaints = complaints_list.filter(complaint_type='Faculty').count()
    hod_complaints = complaints_list.filter(complaint_type='HOD').count()
    staff_complaints = complaints_list.filter(complaint_type='Staff').count()
    facility_complaints = complaints_list.filter(complaint_type='Facility').count()
    context = {
        'complaints_list': complaints_list,
        'total_complaints': total_complaints,
        'pending': pending,
        'investigating': investigating,
        'resolved': resolved,
        'escalated': escalated,
        'faculty_complaints': faculty_complaints,
        'hod_complaints': hod_complaints,
        'staff_complaints': staff_complaints,
        'facility_complaints': facility_complaints,
        'page_title': 'All Complaints'
    }
    return render(request, 'complaints/admins_complaints_list.html', context)