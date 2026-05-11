# complaints/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count

from .models import Complaint, ComplaintUpdate, ComplaintInvestigation, InvestigationFinding
from .forms import (
    ComplaintSubmissionForm, ComplaintUpdateForm, AssignInvestigationForm,
    InvestigationFindingsForm, HODFinalActionForm,
)
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe
from users.models import User
import json


def create_notification(recipient, title, message, notification_type, link=None):
    from users.models import Notification
    Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )


# ─────────────────────────────────────────────
# STUDENT
# ─────────────────────────────────────────────

@login_required
def submit_complaint(request):
    if request.user.role != 'Student':
        messages.error(request, 'Only students can submit complaints.')
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = ComplaintSubmissionForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.student = request.user
            complaint.save()

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
                        link=f'/complaints/admin/handle/{complaint.id}/',
                    )

            elif complaint.complaint_type == 'Staff':
                if complaint.assigned_to:
                    create_notification(
                        recipient=complaint.assigned_to,
                        title=f'New Staff Complaint: {complaint.subject}',
                        message=f'A complaint has been submitted by {complaint.student.full_name}. Tracking ID: {complaint.tracking_id}',
                        notification_type='complaint',
                        link=f'/complaints/staff/handle/{complaint.id}/',
                    )

            elif complaint.complaint_type == 'Facility':
                if complaint.assigned_to:
                    create_notification(
                        recipient=complaint.assigned_to,
                        title=f'New Facility Issue: {complaint.subject}',
                        message=f'A facility issue has been reported by {complaint.student.full_name}. Tracking ID: {complaint.tracking_id}',
                        notification_type='complaint',
                        link=f'/complaints/staff/handle/{complaint.id}/',
                    )

            messages.success(request, f'Complaint submitted successfully! Tracking ID: {complaint.tracking_id}')
            return redirect('my_complaints')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ComplaintSubmissionForm()

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
    context = {
        'complaints_list': complaints_list,
        'total_complaints': complaints_list.count(),
        'pending': complaints_list.filter(status='Pending').count(),
        'resolved': complaints_list.filter(status='Resolved').count(),
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


# ─────────────────────────────────────────────
# HOD
# ─────────────────────────────────────────────

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
        'findings_submitted': complaints_list.filter(status='Findings Submitted').count(),
        'resolved': complaints_list.filter(status='Resolved').count(),
        'escalated': complaints_list.filter(status='Escalated').count(),
        'page_title': 'Faculty Complaints'
    }
    return render(request, 'complaints/hod_complaints_list.html', context)


@login_required
def handle_complaint(request, complaint_id):
    if request.user.role not in ['HOD', 'Staff', 'DAO', 'Admin']:
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
                return redirect('staff_task_list')
            elif request.user.role == 'DAO':
                return redirect('dao_complaints_list')
            else:
                return redirect('admin_complaints_list')
    else:
        form = ComplaintUpdateForm()

    try:
        investigation = complaint.investigation
        findings = investigation.findings.all()
    except ComplaintInvestigation.DoesNotExist:
        investigation = None
        findings = []

    updates = complaint.updates.all().order_by('created_at')
    context = {
        'form': form,
        'complaint': complaint,
        'updates': updates,
        'investigation': investigation,
        'findings': findings,
        'page_title': f'Handle Complaint {complaint.tracking_id}'
    }
    return render(request, 'complaints/handle_complaint.html', context)


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
                comment=f"Investigation assigned to: {investigator_names}. Brief: {brief_preview}",
                status_changed_to='Under Investigation',
            )

            _notify_investigators(complaint, investigation, request.user)

            create_notification(
                recipient=complaint.student,
                title=f'Your complaint {complaint.tracking_id} is under investigation',
                message=f'Your complaint "{complaint.subject}" has been assigned for investigation. You will be notified when there is an update.',
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
            link=f'/complaints/investigator/my-investigations/',
        )


# ─────────────────────────────────────────────
# INVESTIGATOR (FACULTY)
# ─────────────────────────────────────────────

@login_required
def investigator_dashboard(request):
    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    investigations = ComplaintInvestigation.objects.filter(
        investigators=request.user
    ).select_related('complaint').order_by('-assigned_at')

    already_submitted_ids = set(
        InvestigationFinding.objects.filter(submitted_by=request.user)
        .values_list('investigation_id', flat=True)
    )

    for inv in investigations:
        inv.user_submitted = inv.id in already_submitted_ids

    context = {
        'investigations': investigations,
        'total': investigations.count(),
        'pending': sum(1 for i in investigations if not i.user_submitted),
        'submitted': len(already_submitted_ids),
        'page_title': 'My Investigations',
    }
    return render(request, 'complaints/investigator_dashboard.html', context)


@login_required
def submit_findings(request, investigation_id):
    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    investigation = get_object_or_404(
        ComplaintInvestigation, id=investigation_id, investigators=request.user
    )
    complaint = investigation.complaint

    existing_finding = InvestigationFinding.objects.filter(
        investigation=investigation, submitted_by=request.user
    ).first()

    if request.method == 'POST':
        if existing_finding:
            messages.warning(request, 'You have already submitted findings for this investigation.')
            return redirect('investigator_dashboard')

        form = InvestigationFindingsForm(request.POST)
        if form.is_valid():
            finding = form.save(commit=False)
            finding.investigation = investigation
            finding.submitted_by = request.user
            finding.save()

            if investigation.all_findings_submitted:
                complaint.status = 'Findings Submitted'
                complaint.save()
                all_done = True
            else:
                all_done = False

            notif_msg = (
                f'{request.user.full_name} has submitted investigation findings for '
                f'complaint "{complaint.subject}" (ID: {complaint.tracking_id}). '
                f'Verdict: {finding.verdict}.'
            )
            if all_done:
                notif_msg += ' All investigators have submitted — you can now take final action.'

            create_notification(
                recipient=investigation.assigned_by,
                title=f'Findings submitted for {complaint.tracking_id}',
                message=notif_msg,
                notification_type='complaint',
                link=f'/complaints/hod/handle/{complaint.id}/',
            )

            messages.success(request, 'Findings submitted successfully! The HOD has been notified.')
            return redirect('investigator_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = InvestigationFindingsForm()

    context = {
        'form': form,
        'investigation': investigation,
        'complaint': complaint,
        'existing_finding': existing_finding,
        'page_title': f'Submit Findings — {complaint.tracking_id}',
    }
    return render(request, 'complaints/submit_findings.html', context)


@login_required
def hod_final_action(request, complaint_id):
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied.')
        return redirect('login')

    complaint = get_object_or_404(Complaint, id=complaint_id)

    if complaint.status not in ['Findings Submitted', 'Under Investigation']:
        messages.error(request, 'This complaint is not ready for final action.')
        return redirect('hod_complaints_list')

    try:
        investigation = complaint.investigation
        findings = investigation.findings.all()
    except ComplaintInvestigation.DoesNotExist:
        investigation = None
        findings = []

    if request.method == 'POST':
        form = HODFinalActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            note   = form.cleaned_data['note']

            complaint.final_action_note = note

            if action == 'Resolve':
                complaint.status = 'Resolved'
                complaint.resolved_at = timezone.now()
                student_title = 'Your complaint has been resolved'
                student_msg   = f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) has been resolved. Note from HOD: {note}'

            elif action == 'Escalate':
                complaint.status = 'Escalated'
                admin = User.objects.filter(role='Admin').first()
                complaint.assigned_to = admin
                student_title = 'Your complaint has been escalated'
                student_msg   = f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) has been escalated to Admin for further action.'
                if admin:
                    create_notification(
                        recipient=admin,
                        title=f'Escalated Complaint: {complaint.tracking_id}',
                        message=f'HOD {request.user.full_name} has escalated complaint {complaint.tracking_id} to you.',
                        notification_type='complaint',
                        link=f'/complaints/admin/handle/{complaint.id}/',
                    )

            elif action == 'More Investigation':
                complaint.status = 'Under Investigation'
                if investigation:
                    investigation.findings.all().delete()
                    _notify_investigators(complaint, investigation, request.user)
                student_title = 'Further investigation requested on your complaint'
                student_msg   = f'The HOD has reviewed the findings for "{complaint.subject}" and requested further investigation. You will be notified when complete.'

            complaint.save()

            ComplaintUpdate.objects.create(
                complaint=complaint,
                updated_by=request.user,
                comment=f'Final action: {action}. Note to student: {note}',
                status_changed_to=complaint.status,
            )

            create_notification(
                recipient=complaint.student,
                title=student_title,
                message=student_msg,
                notification_type='update',
                link=f'/complaints/detail/{complaint.id}/',
            )

            messages.success(request, f'Action "{action}" applied successfully.')
            return redirect('hod_complaints_list')
        else:
            messages.error(request, 'Please correct the errors.')
    else:
        form = HODFinalActionForm()

    context = {
        'form': form,
        'complaint': complaint,
        'investigation': investigation,
        'findings': findings,
        'page_title': f'Final Action — {complaint.tracking_id}',
    }
    return render(request, 'complaints/hod_final_action.html', context)


# ─────────────────────────────────────────────
# STAFF
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# ADMIN
# ─────────────────────────────────────────────

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
def dao_complaints_list(request):
    if request.user.role != 'DAO':
        messages.error(request, 'Access denied.')
        return redirect('login')

    complaints_list = Complaint.objects.filter(
        assigned_to=request.user
    ).order_by('-submitted_at')

    staff_list = User.objects.filter(role='Staff', is_active=True)

    total_complaints = complaints_list.count()
    pending   = complaints_list.filter(status='Pending').count()
    resolved  = complaints_list.filter(status='Resolved').count()
    escalated = complaints_list.filter(status='Escalated').count()

    context = {
        'complaints_list': complaints_list,
        'staff_list': staff_list,
        'total_complaints': total_complaints,
        'pending': pending,
        'resolved': resolved,
        'escalated': escalated,
        'page_title': 'DAO Complaints',
    }
    return render(request, 'complaints/dao_complaints_list.html', context)


@login_required
def dao_assign_staff(request, complaint_id):
    if request.user.role != 'DAO':
        messages.error(request, 'Access denied.')
        return redirect('login')

    complaint = get_object_or_404(Complaint, id=complaint_id)
    staff_id  = request.POST.get('staff_id')

    if not staff_id:
        messages.error(request, 'Please select a staff member.')
        return redirect('dao_complaints_list')

    staff = get_object_or_404(User, id=staff_id, role='Staff')

    # Save DAO as the original assignee in a comment
    ComplaintUpdate.objects.create(
        complaint=complaint,
        updated_by=request.user,
        comment=f'Complaint assigned to Staff member {staff.full_name} for physical resolution.',
        status_changed_to='Under Investigation',
    )

    complaint.status = 'Under Investigation'
    complaint.assigned_to = staff
    complaint.save()

    # Notify staff
    from users.models import Notification
    Notification.objects.create(
        recipient=staff,
        title=f'New Task Assigned: {complaint.tracking_id}',
        message=f'DAO has assigned you a facility complaint "{complaint.subject}". Please attend to it promptly.',
        notification_type='complaint',
        link=f'/complaints/detail/{complaint.id}/',
    )

    # Notify student
    Notification.objects.create(
        recipient=complaint.student,
        title=f'Your complaint is being handled',
        message=f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) has been assigned to a staff member for resolution.',
        notification_type='update',
        link=f'/complaints/detail/{complaint.id}/',
    )

    messages.success(request, f'Complaint assigned to {staff.full_name}. Both staff and student have been notified.')
    return redirect('dao_complaints_list')


@login_required
def dao_escalate_complaint(request, complaint_id):
    if request.user.role != 'DAO':
        messages.error(request, 'Access denied.')
        return redirect('login')

    complaint = get_object_or_404(Complaint, id=complaint_id)
    head = User.objects.filter(role='HOD', department=complaint.student.department).first()
    if not head:
        head = User.objects.filter(role='Admin').first()

    if head:
        ComplaintUpdate.objects.create(
            complaint=complaint,
            updated_by=request.user,
            comment=f'Complaint escalated to Head ({head.full_name}) by DAO as it requires higher authority attention.',
            status_changed_to='Escalated',
        )

        complaint.assigned_to = head
        complaint.status = 'Escalated'
        complaint.save()

        from users.models import Notification
        # Notify head
        Notification.objects.create(
            recipient=head,
            title=f'Escalated Complaint: {complaint.tracking_id}',
            message=f'Complaint "{complaint.subject}" has been escalated to you by DAO {request.user.full_name}.',
            notification_type='complaint',
            link=f'/complaints/detail/{complaint.id}/',
        )

        # Notify student
        Notification.objects.create(
            recipient=complaint.student,
            title=f'Your complaint has been escalated',
            message=f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) has been escalated to the Head for review as it requires higher authority attention.',
            notification_type='update',
            link=f'/complaints/detail/{complaint.id}/',
        )

        messages.success(request, f'Complaint escalated to {head.full_name}. Student has been notified.')
    else:
        messages.error(request, 'No head found to escalate to.')

    return redirect('dao_complaints_list')


@login_required
def staff_task_list(request):
    if request.user.role != 'Staff':
        messages.error(request, 'Access denied.')
        return redirect('login')

    tasks = Complaint.objects.filter(
        assigned_to=request.user
    ).order_by('-submitted_at')

    total    = tasks.count()
    pending  = tasks.filter(status='Pending').count()
    active   = tasks.filter(status='Under Investigation').count()
    resolved = tasks.filter(status='Resolved').count()

    context = {
        'tasks': tasks,
        'total': total,
        'pending': pending,
        'active': active,
        'resolved': resolved,
    }
    return render(request, 'complaints/staff_task_list.html', context)


@login_required
def staff_mark_fixed(request, complaint_id):
    if request.user.role != 'Staff':
        messages.error(request, 'Access denied.')
        return redirect('login')

    complaint = get_object_or_404(Complaint, id=complaint_id, assigned_to=request.user)

    ComplaintUpdate.objects.create(
        complaint=complaint,
        updated_by=request.user,
        comment='Staff has completed the physical work. Marked as Fixed — awaiting DAO final review.',
        status_changed_to='Resolved',
    )

    complaint.status = 'Resolved'
    complaint.resolved_at = timezone.now()
    complaint.save()

    from users.models import Notification
    # Notify student
    Notification.objects.create(
        recipient=complaint.student,
        title=f'Your complaint has been resolved',
        message=f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) has been resolved by our staff team.',
        notification_type='update',
        link=f'/complaints/detail/{complaint.id}/',
    )

    messages.success(request, 'Complaint marked as resolved. Student has been notified.')
    return redirect('staff_task_list')