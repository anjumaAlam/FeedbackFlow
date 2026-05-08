# complaints/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count

from .models import Complaint, ComplaintUpdate, ComplaintInvestigation
from .forms import ComplaintSubmissionForm, ComplaintUpdateForm, AssignInvestigationForm
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe
from users.models import User
import json


def create_notification(recipient, title, message, notification_type, link=None):
    """Helper to create a notification"""
    from users.models import Notification
    Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )


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

            # --- NOTIFICATION ---
            if complaint.complaint_type == 'Faculty':
                if complaint.assigned_to:
                    create_notification(
                        recipient=complaint.assigned_to,
                        title=f'New Faculty Complaint: {complaint.subject}',
                        message=f'A new complaint has been submitted by {complaint.student.full_name}. Tracking ID: {complaint.tracking_id}',
                        notification_type='complaint',
                        link=f'/complaints/hod/handle/{complaint.id}/',
                    )

            elif complaint.complaint_type == 'HOD':
                for admin in User.objects.filter(role='Admin'):
                    create_notification(
                        recipient=admin,
                        title=f'New HOD Complaint: {complaint.subject}',
                        message=f'A complaint against HOD has been submitted by {complaint.student.full_name}. Tracking ID: {complaint.tracking_id}',
                        notification_type='complaint',
                        link=f'/complaints/admin/list/',
                    )

            elif complaint.complaint_type == 'Staff':
                # ✅ Notify only the assigned staff member (same department as student)
                if complaint.assigned_to:
                    create_notification(
                        recipient=complaint.assigned_to,
                        title=f'New Staff Complaint: {complaint.subject}',
                        message=f'A complaint has been submitted by {complaint.student.full_name}. Tracking ID: {complaint.tracking_id}',
                        notification_type='complaint',
                        link=f'/complaints/staff/list/',
                    )

            elif complaint.complaint_type == 'Facility':
                if complaint.assigned_to:
                    create_notification(
                        recipient=complaint.assigned_to,
                        title=f'New Facility Issue: {complaint.subject}',
                        message=f'A facility issue has been reported by {complaint.student.full_name}. Tracking ID: {complaint.tracking_id}',
                        notification_type='complaint',
                        link=f'/complaints/staff/list/',
                    )
            # --- END NOTIFICATION ---

            messages.success(
                request,
                f'Complaint submitted successfully! Tracking ID: {complaint.tracking_id}'
            )
            return redirect('my_complaints')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ComplaintSubmissionForm()

    # ✅ Faculty and Staff both filtered to student's own department
    roles = ['Faculty', 'HOD', 'Staff']
    users_by_role = {}
    for r in roles:
        qs = User.objects.filter(role=r, is_active=True).order_by('full_name')
        if r in ['Faculty', 'Staff']:
            qs = qs.filter(department=request.user.department)
        users_by_role[r] = [{'id': u.id, 'name': u.full_name} for u in qs]

    context = {
        'form': form,
        'page_title': 'Submit Complaint',
        'users_by_role': users_by_role,
    }
    return render(request, 'complaints/submit_complaints.html', context)


@login_required
def my_complaints(request):
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
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied. HOD only.')
        return redirect('login')

    complaints_list = Complaint.objects.filter(
        Q(assigned_to=request.user) |
        Q(faculty_concerned__department=request.user.department)
    ).distinct().order_by('-submitted_at')

    context = {
        'complaints_list': complaints_list,
        'total_complaints': complaints_list.count(),
        'pending': complaints_list.filter(status='Pending').count(),
        'investigating': complaints_list.filter(status='Under Investigation').count(),
        'resolved': complaints_list.filter(status='Resolved').count(),
        'escalated': complaints_list.filter(status='Escalated').count(),
        'page_title': 'Faculty Complaints'
    }
    return render(request, 'complaints/hod_complaints_list.html', context)


@login_required
def handle_complaint(request, complaint_id):
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

            create_notification(
                recipient=complaint.student,
                title=f'Update on your complaint: {complaint.tracking_id}',
                message=f'Your complaint "{complaint.subject}" has been updated. New status: {complaint.status}',
                notification_type='update',
                link=f'/complaints/detail/{complaint.id}/',
            )

            messages.success(request, 'Complaint updated successfully!')

            if request.user.role == 'HOD':
                return redirect('hod_complaints_list')
            elif request.user.role == 'Staff':
                return redirect('staff_complaints_list')
            else:
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
    if request.user.role != 'Staff':
        messages.error(request, 'Access denied. Staff only.')
        return redirect('login')

    complaints_list = Complaint.objects.filter(assigned_to=request.user).order_by('-submitted_at')

    context = {
        'complaints_list': complaints_list,
        'total_complaints': complaints_list.count(),
        'pending': complaints_list.filter(status='Pending').count(),
        'investigating': complaints_list.filter(status='Under Investigation').count(),
        'resolved': complaints_list.filter(status='Resolved').count(),
        'page_title': 'Staff & Facility Complaints'
    }
    return render(request, 'complaints/staff_complaints_list.html', context)


@login_required
def admin_complaints_list(request):
    if request.user.role != 'Admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('login')

    complaints_list = Complaint.objects.all().order_by('-submitted_at')

    context = {
        'complaints_list': complaints_list,
        'total_complaints': complaints_list.count(),
        'pending': complaints_list.filter(status='Pending').count(),
        'investigating': complaints_list.filter(status='Under Investigation').count(),
        'resolved': complaints_list.filter(status='Resolved').count(),
        'escalated': complaints_list.filter(status='Escalated').count(),
        'faculty_complaints': complaints_list.filter(complaint_type='Faculty').count(),
        'hod_complaints': complaints_list.filter(complaint_type='HOD').count(),
        'staff_complaints': complaints_list.filter(complaint_type='Staff').count(),
        'facility_complaints': complaints_list.filter(complaint_type='Facility').count(),
        'page_title': 'All Complaints'
    }
    return render(request, 'complaints/admins_complaints_list.html', context)


@login_required
def assign_investigation(request, complaint_id):
    if request.user.role not in ['HOD', 'Admin']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    complaint = get_object_or_404(Complaint, id=complaint_id)

    if request.user.role == 'HOD':
        in_dept = (
            (complaint.assigned_to == request.user) or
            (complaint.faculty_concerned and complaint.faculty_concerned.department == request.user.department) or
            (complaint.student.department == request.user.department)
        )
        if not in_dept:
            messages.error(request, 'This complaint is not in your department.')
            return redirect('hod_complaints_list')

    try:
        existing = complaint.investigation
    except ComplaintInvestigation.DoesNotExist:
        existing = None

    if request.method == 'POST':
        form = AssignInvestigationForm(
            request.POST,
            instance=existing,
            complaint=complaint,
            hod_user=request.user,
        )
        if form.is_valid():
            investigation = form.save(commit=False)
            investigation.complaint = complaint
            investigation.assigned_by = request.user
            investigation.save()
            form.save_m2m()

            complaint.status = 'Under Investigation'
            complaint.save()

            investigator_names = ', '.join(i.full_name for i in investigation.investigators.all())
            brief_preview = investigation.description[:200]
            if len(investigation.description) > 200:
                brief_preview += '...'

            ComplaintUpdate.objects.create(
                complaint=complaint,
                updated_by=request.user,
                comment=(
                    f"Investigation assigned to: {investigator_names}. "
                    f"Brief: {brief_preview}"
                ),
                status_changed_to='Under Investigation',
            )

            _notify_investigators(complaint, investigation, request.user)

            create_notification(
                recipient=complaint.student,
                title=f'Your complaint {complaint.tracking_id} is under investigation',
                message=(
                    f'Your complaint "{complaint.subject}" has been assigned for investigation. '
                    f'You will be notified when there is an update.'
                ),
                notification_type='complaint',
                link=f'/complaints/detail/{complaint.id}/',
            )

            messages.success(request, f'Investigation assigned successfully to {investigator_names}.')
            return redirect('handle_complaint', complaint_id=complaint.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AssignInvestigationForm(
            instance=existing,
            complaint=complaint,
            hod_user=request.user,
        )

    context = {
        'form': form,
        'complaint': complaint,
        'existing_investigation': existing,
        'page_title': f'Assign Investigation – {complaint.tracking_id}',
    }
    return render(request, 'complaints/assign_investigation.html', context)


def _notify_investigators(complaint, investigation, assigned_by):
    from users.models import Notification
    for investigator in investigation.investigators.all():
        Notification.objects.create(
            recipient=investigator,
            title=f'You have been assigned to investigate complaint {complaint.tracking_id}',
            message=(
                f'HOD {assigned_by.full_name} has assigned you to investigate:\n'
                f'Subject: {complaint.subject}\n\n'
                f'Brief:\n{investigation.description[:400]}'
            ),
            notification_type='complaint',
            link=f'/complaints/detail/{complaint.id}/',
        )