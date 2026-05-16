# complaints/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count

from .models import Complaint, ComplaintUpdate, ComplaintInvestigation, InvestigationFinding, ClarificationRequest
from .forms import (
    ComplaintSubmissionForm, ComplaintUpdateForm, AssignInvestigationForm,
    InvestigationFindingsForm, HODFinalActionForm,
    ClarificationResponseForm,
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

            noun = 'Complaint'
            if complaint.complaint_type in ['Advice', 'Opinion']:
                noun = complaint.complaint_type
            elif complaint.complaint_type == 'Facility':
                noun = 'Issue'

            if complaint.assigned_to:
                handler_link = f'/complaints/hod/handle/{complaint.id}/'
                create_notification(
                    recipient=complaint.assigned_to,
                    title=f'New {noun} Received: {complaint.subject}',
                    message=f'A new {noun.lower()} has been submitted. Tracking ID: {complaint.tracking_id}',
                    notification_type='complaint',
                    link=handler_link,
                )

            create_notification(
                recipient=request.user,
                title=f'{noun} Submitted Successfully ✅',
                message=f'Your {noun.lower()} "{complaint.subject}" has been received. '
                        f'Tracking ID: {complaint.tracking_id}. '
                        f'It has been assigned to the appropriate handler and you will be notified of any updates.',
                notification_type='complaint',
                link=f'/complaints/detail/{complaint.id}/',
            )

            messages.success(request, f'{noun} submitted successfully! Tracking ID: {complaint.tracking_id}')
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

    mode = request.GET.get('mode', 'all')

    complaints_list = Complaint.objects.filter(
        Q(assigned_to=request.user) |
        Q(faculty_concerned__department=request.user.department)
    ).distinct().order_by('-submitted_at')

    context = {
        'complaints_list': complaints_list,
        'mode': mode,
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

    elif request.user.role == 'DAO':
        dao_touched = ComplaintUpdate.objects.filter(
            complaint=complaint, updated_by=request.user
        ).exists()
        if complaint.assigned_to != request.user and not dao_touched:
            messages.error(request, 'This complaint is not assigned to you.')
            return redirect('dao_complaints_list')

    elif request.user.role == 'Staff':
        if complaint.assigned_to != request.user:
            messages.error(request, 'This complaint is not assigned to you.')
            return redirect('staff_task_list')

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
                elif update.status_changed_to == 'Escalated':
                    noun = 'Complaint'
                    if complaint.complaint_type in ['Advice', 'Opinion']:
                        noun = complaint.complaint_type
                    elif complaint.complaint_type == 'Facility':
                        noun = 'Issue'
                    for admin in User.objects.filter(role='Admin'):
                        create_notification(
                            recipient=admin,
                            title=f'{noun} Escalated: {complaint.tracking_id}',
                            message=f'"{complaint.subject}" has been escalated by {request.user.full_name}.',
                            notification_type='complaint',
                            link=f'/complaints/hod/handle/{complaint.id}/',
                        )
                complaint.save()

            noun = 'Complaint'
            if complaint.complaint_type in ['Advice', 'Opinion']:
                noun = complaint.complaint_type
            elif complaint.complaint_type == 'Facility':
                noun = 'Issue'

            create_notification(
                recipient=complaint.student,
                title=f'Update on your {noun.lower()}: {complaint.tracking_id}',
                message=f'Your {noun.lower()} "{complaint.subject}" has been updated. New status: {complaint.status}',
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

    # ── Build findings_with_status for clarification panel ──
    try:
        investigation = complaint.investigation
        raw_findings  = investigation.findings.all()
        findings_with_status = []
        for finding in raw_findings:
            clarifications = ClarificationRequest.objects.filter(finding=finding)
            all_responded  = clarifications.exists() and all(
                c.status == 'Responded' for c in clarifications
            )
            findings_with_status.append({
                'finding':        finding,
                'clarifications': clarifications,
                'all_responded':  all_responded,
                'any_sent':       clarifications.exists(),
            })
    except ComplaintInvestigation.DoesNotExist:
        investigation        = None
        findings_with_status = []

    updates = complaint.updates.all().order_by('created_at')
    context = {
        'form':                 form,
        'complaint':            complaint,
        'updates':              updates,
        'investigation':        investigation,
        'findings_with_status': findings_with_status,
        'page_title':           f'Handle Complaint {complaint.tracking_id}'
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
            request.POST, instance=existing, complaint=complaint, hod_user=request.user,
        )
        if form.is_valid():
            investigation = form.save(commit=False)
            investigation.complaint   = complaint
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
                message=f'Your complaint "{complaint.subject}" has been assigned for investigation.',
                notification_type='complaint',
                link=f'/complaints/detail/{complaint.id}/',
            )

            messages.success(request, f'Investigation assigned successfully to {investigator_names}.')
            return redirect('handle_complaint', complaint_id=complaint.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AssignInvestigationForm(instance=existing, complaint=complaint, hod_user=request.user)

    context = {
        'form':                   form,
        'complaint':              complaint,
        'existing_investigation': existing,
        'page_title':             f'Assign Investigation – {complaint.tracking_id}',
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
        'total':          investigations.count(),
        'pending':        sum(1 for i in investigations if not i.user_submitted),
        'submitted':      len(already_submitted_ids),
        'page_title':     'My Investigations',
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
            finding               = form.save(commit=False)
            finding.investigation = investigation
            finding.submitted_by  = request.user
            finding.save()

            if finding.verdict == 'Needs More Info':
                clarification_needed = []
                if finding.needs_student_clarification:
                    clarification_needed.append('Student')
                if finding.needs_faculty_statement:
                    clarification_needed.append('Accused Faculty')

                create_notification(
                    recipient=investigation.assigned_by,
                    title=f'⚠️ Clarification Needed — {complaint.tracking_id}',
                    message=(
                        f'{request.user.full_name} needs clarification from: {", ".join(clarification_needed)}.\n\n'
                        f'Questions:\n{finding.clarification_questions}\n\n'
                        f'Please review and forward the clarification request from the complaint handle page.'
                    ),
                    notification_type='complaint',
                    link=f'/complaints/hod/handle/{complaint.id}/',
                )

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
        'form':             form,
        'investigation':    investigation,
        'complaint':        complaint,
        'existing_finding': existing_finding,
        'page_title':       f'Submit Findings — {complaint.tracking_id}',
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
        findings      = investigation.findings.all()
    except ComplaintInvestigation.DoesNotExist:
        investigation = None
        findings      = []

    if request.method == 'POST':
        form = HODFinalActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            note   = form.cleaned_data['note']

            complaint.final_action_note = note

            if action == 'Resolve':
                complaint.status      = 'Resolved'
                complaint.resolved_at = timezone.now()
                student_title = 'Your complaint has been resolved'
                student_msg   = f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) has been resolved. Note from HOD: {note}'

            elif action == 'Escalate':
                complaint.status      = 'Escalated'
                admin                 = User.objects.filter(role='Admin').first()
                complaint.assigned_to = admin
                student_title = 'Your complaint has been escalated'
                student_msg   = f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) has been escalated to Admin.'
                if admin:
                    create_notification(
                        recipient=admin,
                        title=f'Escalated Complaint: {complaint.tracking_id}',
                        message=f'HOD {request.user.full_name} has escalated complaint {complaint.tracking_id} to you.',
                        notification_type='complaint',
                        link=f'/complaints/hod/handle/{complaint.id}/',
                    )

            elif action == 'More Investigation':
                complaint.status = 'Under Investigation'
                if investigation:
                    investigation.findings.all().delete()
                    _notify_investigators(complaint, investigation, request.user)
                student_title = 'Further investigation requested on your complaint'
                student_msg   = f'The HOD has reviewed the findings for "{complaint.subject}" and requested further investigation.'

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
        'form':          form,
        'complaint':     complaint,
        'investigation': investigation,
        'findings':      findings,
        'page_title':    f'Final Action — {complaint.tracking_id}',
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
        'complaints_list':  complaints_list,
        'total_complaints': complaints_list.count(),
        'pending':          complaints_list.filter(status='Pending').count(),
        'investigating':    complaints_list.filter(status='Under Investigation').count(),
        'resolved':         complaints_list.filter(status='Resolved').count(),
        'page_title':       'Staff & Facility Complaints'
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
        'complaints_list':    complaints_list,
        'total_complaints':   complaints_list.count(),
        'pending':            complaints_list.filter(status='Pending').count(),
        'investigating':      complaints_list.filter(status='Under Investigation').count(),
        'resolved':           complaints_list.filter(status='Resolved').count(),
        'escalated':          complaints_list.filter(status='Escalated').count(),
        'faculty_complaints': complaints_list.filter(complaint_type='Faculty').count(),
        'hod_complaints':     complaints_list.filter(complaint_type='HOD').count(),
        'staff_complaints':   complaints_list.filter(complaint_type='Staff').count(),
        'facility_complaints':complaints_list.filter(complaint_type='Facility').count(),
        'advice_complaints':  complaints_list.filter(complaint_type='Advice').count(),
        'opinion_complaints': complaints_list.filter(complaint_type='Opinion').count(),
        'page_title':         'All Complaints'
    }
    return render(request, 'complaints/admins_complaints_list.html', context)


@login_required
def dao_complaints_list(request):
    if request.user.role != 'DAO':
        messages.error(request, 'Access denied.')
        return redirect('login')

    dao_handled_ids = ComplaintUpdate.objects.filter(
        updated_by=request.user
    ).values_list('complaint_id', flat=True)

    complaints_list = Complaint.objects.filter(
        Q(assigned_to=request.user) | Q(id__in=dao_handled_ids)
    ).distinct().order_by('-submitted_at')

    staff_list = User.objects.filter(role='Staff', is_active=True)

    context = {
        'complaints_list':  complaints_list,
        'staff_list':       staff_list,
        'total_complaints': complaints_list.count(),
        'pending':          complaints_list.filter(status='Pending').count(),
        'resolved':         complaints_list.filter(status='Resolved').count(),
        'escalated':        complaints_list.filter(status='Escalated').count(),
        'page_title':       'DAO Complaints',
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

    ComplaintUpdate.objects.create(
        complaint=complaint,
        updated_by=request.user,
        comment='Complaint assigned to a staff member for physical resolution.',
        status_changed_to='Under Investigation',
    )

    complaint.status      = 'Under Investigation'
    complaint.assigned_to = staff
    complaint.save()

    from users.models import Notification
    Notification.objects.create(
        recipient=staff,
        title=f'New Task Assigned: {complaint.tracking_id}',
        message=f'You have been assigned a facility complaint "{complaint.subject}". Please attend to it promptly.',
        notification_type='complaint',
        link=f'/complaints/detail/{complaint.id}/',
    )
    Notification.objects.create(
        recipient=complaint.student,
        title='Your complaint is being handled',
        message=f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) is currently being handled by our team.',
        notification_type='update',
        link=f'/complaints/detail/{complaint.id}/',
    )

    messages.success(request, f'Complaint assigned to {staff.full_name}.')
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
            comment='Complaint escalated to Head for higher authority review.',
            status_changed_to='Escalated',
        )
        complaint.assigned_to = head
        complaint.status      = 'Escalated'
        complaint.save()

        from users.models import Notification
        Notification.objects.create(
            recipient=head,
            title=f'Escalated Complaint: {complaint.tracking_id}',
            message=f'Complaint "{complaint.subject}" has been escalated to you by DAO {request.user.full_name}.',
            notification_type='complaint',
            link=f'/complaints/hod/handle/{complaint.id}/',
        )
        Notification.objects.create(
            recipient=complaint.student,
            title='Your complaint is being reviewed',
            message=f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) is currently being reviewed.',
            notification_type='update',
            link=f'/complaints/detail/{complaint.id}/',
        )
        messages.success(request, f'Complaint escalated to {head.full_name}.')
    else:
        messages.error(request, 'No head found to escalate to.')

    return redirect('dao_complaints_list')


@login_required
def staff_task_list(request):
    if request.user.role != 'Staff':
        messages.error(request, 'Access denied.')
        return redirect('login')

    status_filter = request.GET.get('status', '')
    tasks = Complaint.objects.filter(assigned_to=request.user).order_by('-submitted_at')
    if status_filter == 'pending':
        tasks = tasks.filter(status='Pending')

    context = {
        'tasks':         tasks,
        'total':         tasks.count(),
        'pending':       tasks.filter(status='Pending').count(),
        'active':        tasks.filter(status='Under Investigation').count(),
        'resolved':      tasks.filter(status='Resolved').count(),
        'status_filter': status_filter,
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
        comment='Staff has completed the physical work. Marked as Fixed.',
        status_changed_to='Resolved',
    )
    complaint.status      = 'Resolved'
    complaint.resolved_at = timezone.now()
    complaint.save()

    from users.models import Notification
    Notification.objects.create(
        recipient=complaint.student,
        title='Your complaint has been resolved',
        message=f'Your complaint "{complaint.subject}" (ID: {complaint.tracking_id}) has been resolved.',
        notification_type='update',
        link=f'/complaints/detail/{complaint.id}/',
    )
    messages.success(request, 'Complaint marked as resolved. Student has been notified.')
    return redirect('staff_task_list')


# ─────────────────────────────────────────────────────────────────────────────
# FACULTY COMPLAINT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def faculty_complaint_summary(request):
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied. HOD only.')
        return redirect('login')

    from .utils import (
        get_faculty_complaints_summary, group_similar_complaints,
        get_complaint_statistics, get_top_complaint_subjects,
        get_department_complaint_comparison
    )

    faculty_id      = request.GET.get('faculty_id') or request.POST.get('faculty_id')
    faculty_in_dept = User.objects.filter(
        role='Faculty', department=request.user.department, is_active=True
    ).order_by('full_name')

    context = {
        'page_title':       'Faculty Complaint Analysis',
        'faculty_list':     faculty_in_dept,
        'selected_faculty': None,
        'summary_data':     None,
        'statistics':       None,
        'similar_groups':   None,
        'top_subjects':     None,
        'comparison_data':  None,
    }

    if faculty_id:
        try:
            selected_faculty = User.objects.get(id=faculty_id, role='Faculty')
            summary_data     = get_faculty_complaints_summary(selected_faculty)
            all_complaints   = summary_data['all_complaints']
            comparison_data  = get_department_complaint_comparison(selected_faculty)

            if all_complaints.exists():
                similar_groups = group_similar_complaints(list(all_complaints), similarity_threshold=0.55)
                statistics     = get_complaint_statistics(all_complaints)
                top_subjects   = get_top_complaint_subjects(all_complaints, limit=5)
                context.update({
                    'selected_faculty': selected_faculty,
                    'summary_data':     summary_data,
                    'statistics':       statistics,
                    'similar_groups':   similar_groups,
                    'top_subjects':     top_subjects,
                    'comparison_data':  comparison_data,
                })
            else:
                messages.info(request, f'No complaints found for {selected_faculty.full_name}')
                context.update({
                    'selected_faculty': selected_faculty,
                    'comparison_data':  comparison_data,
                })
        except User.DoesNotExist:
            messages.error(request, 'Faculty not found.')

    return render(request, 'complaints/faculty_complaint_summary.html', context)


@login_required
def faculty_course_wise_complaints(request, faculty_id):
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied. HOD only.')
        return redirect('login')

    faculty = get_object_or_404(User, id=faculty_id, role='Faculty')
    if faculty.department != request.user.department:
        messages.error(request, 'You can only view faculty from your department.')
        return redirect('faculty_complaint_summary')

    from feedback.models import CourseAssignment
    course_assignments    = CourseAssignment.objects.filter(faculty=faculty).select_related('course')
    course_complaint_data = []

    for assignment in course_assignments:
        course            = assignment.course
        course_complaints = Complaint.objects.filter(
            faculty_concerned=faculty, complaint_type='Faculty',
            student__department=course.department
        )
        if course_complaints.exists():
            course_complaint_data.append({
                'course':           course,
                'assignment':       assignment,
                'total_complaints': course_complaints.count(),
                'pending':          course_complaints.filter(status='Pending').count(),
                'resolved':         course_complaints.filter(status='Resolved').count(),
                'investigating':    course_complaints.filter(status='Under Investigation').count(),
                'high_priority':    course_complaints.filter(priority__in=['High', 'Urgent']).count(),
                'complaints':       course_complaints.order_by('-submitted_at'),
            })

    course_complaint_data.sort(key=lambda x: x['total_complaints'], reverse=True)

    context = {
        'page_title':            f'Course-wise Complaints - {faculty.full_name}',
        'faculty':               faculty,
        'course_complaint_data': course_complaint_data,
        'total_complaints':      sum(c['total_complaints'] for c in course_complaint_data),
    }
    return render(request, 'complaints/faculty_course_wise_complaints.html', context)


@login_required
def similar_complaints_detail(request, faculty_id, group_index):
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied. HOD only.')
        return redirect('login')

    from .utils import get_faculty_complaints_summary, group_similar_complaints

    faculty = get_object_or_404(User, id=faculty_id, role='Faculty')
    if faculty.department != request.user.department:
        messages.error(request, 'You can only view faculty from your department.')
        return redirect('faculty_complaint_summary')

    summary_data   = get_faculty_complaints_summary(faculty)
    all_complaints = list(summary_data['all_complaints'])
    similar_groups = group_similar_complaints(all_complaints, similarity_threshold=0.55)

    if 0 <= group_index < len(similar_groups):
        group = similar_groups[group_index]
    else:
        messages.error(request, 'Group not found.')
        return redirect('faculty_complaint_summary')

    context = {
        'page_title':   'Similar Complaints Detail',
        'faculty':      faculty,
        'group':        group,
        'group_index':  group_index,
        'total_groups': len(similar_groups),
    }
    return render(request, 'complaints/similar_complaints_detail.html', context)


def public_log(request):
    type_filter = request.GET.get('type', '')
    complaints  = Complaint.objects.filter(status='Resolved').order_by('-resolved_at')
    if type_filter:
        complaints = complaints.filter(complaint_type=type_filter)
    complaints = complaints[:50]

    all_resolved = Complaint.objects.filter(status='Resolved')
    type_counts  = {
        'all':      all_resolved.count(),
        'Faculty':  all_resolved.filter(complaint_type='Faculty').count(),
        'HOD':      all_resolved.filter(complaint_type='HOD').count(),
        'Staff':    all_resolved.filter(complaint_type='Staff').count(),
        'Facility': all_resolved.filter(complaint_type='Facility').count(),
        'Advice':   all_resolved.filter(complaint_type='Advice').count(),
        'Opinion':  all_resolved.filter(complaint_type='Opinion').count(),
    }
    context = {
        'complaints':  complaints,
        'type_filter': type_filter,
        'type_counts': type_counts,
        'page_title':  'Public Resolved Issues Log'
    }
    return render(request, 'complaints/public_log.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# CLARIFICATION FLOW
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def hod_send_clarification(request, finding_id):
    """HOD reviews investigator's request and forwards to student/faculty."""
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied.')
        return redirect('login')

    finding       = get_object_or_404(InvestigationFinding, id=finding_id)
    complaint     = finding.investigation.complaint
    investigation = finding.investigation

    if investigation.assigned_by != request.user:
        messages.error(request, 'Access denied.')
        return redirect('hod_complaints_list')

    already_sent = ClarificationRequest.objects.filter(finding=finding).exists()

    if request.method == 'POST' and not already_sent:
        parties = []

        if finding.needs_student_clarification:
            ClarificationRequest.objects.create(
                finding=finding,
                requested_by=request.user,
                request_type='Student',
                questions=finding.clarification_questions,
                target_user=complaint.student,
            )
            create_notification(
                recipient=complaint.student,
                title=f'📋 Clarification Needed — Complaint {complaint.tracking_id}',
                message=(
                    f'The HOD has forwarded a request for additional information '
                    f'regarding your complaint "{complaint.subject}". '
                    f'Please check your clarification requests and respond promptly.'
                ),
                notification_type='complaint',
                link='/complaints/clarifications/',
            )
            parties.append('Student')

        if finding.needs_faculty_statement and complaint.faculty_concerned:
            ClarificationRequest.objects.create(
                finding=finding,
                requested_by=request.user,
                request_type='Faculty',
                questions=finding.clarification_questions,
                target_user=complaint.faculty_concerned,
            )
            create_notification(
                recipient=complaint.faculty_concerned,
                title=f'📋 Statement Required — Complaint {complaint.tracking_id}',
                message=(
                    f'The HOD requires a statement from you regarding complaint '
                    f'"{complaint.subject}" (ID: {complaint.tracking_id}). '
                    f'Please check your clarification requests and respond promptly.'
                ),
                notification_type='complaint',
                link='/complaints/clarifications/',
            )
            parties.append('Accused Faculty')

        create_notification(
            recipient=finding.submitted_by,
            title=f'✅ Clarification Requests Sent — {complaint.tracking_id}',
            message=(
                f'HOD {request.user.full_name} has forwarded your clarification request '
                f'to: {", ".join(parties)}. You will be notified once they respond.'
            ),
            notification_type='complaint',
            link=f'/complaints/investigator/clarification/{finding.id}/responses/',
        )

        ComplaintUpdate.objects.create(
            complaint=complaint,
            updated_by=request.user,
            comment=f'Clarification request sent to: {", ".join(parties)}. Awaiting responses.',
        )

        messages.success(request, f'Clarification request sent to {", ".join(parties)}.')
        return redirect('handle_complaint', complaint_id=complaint.id)

    context = {
        'finding':      finding,
        'complaint':    complaint,
        'already_sent': already_sent,
        'page_title':   f'Send Clarification — {complaint.tracking_id}',
    }
    return render(request, 'complaints/hod_send_clarification.html', context)


@login_required
def hod_forward_clarification(request, finding_id):
    """Kept for backward compatibility — redirects to hod_send_clarification."""
    return redirect('hod_send_clarification', finding_id=finding_id)


@login_required
def clarification_list(request):
    """Student or Faculty sees their clarification requests."""
    if request.user.role == 'Student':
        clarification_requests = ClarificationRequest.objects.filter(
            target_user=request.user,
            request_type='Student',
        ).select_related('finding__investigation__complaint').order_by('-created_at')
    elif request.user.role in ['Faculty', 'HOD']:
        clarification_requests = ClarificationRequest.objects.filter(
            target_user=request.user,
            request_type='Faculty',
        ).select_related('finding__investigation__complaint').order_by('-created_at')
    else:
        messages.error(request, 'Access denied.')
        return redirect('login')

    context = {
        'clarification_requests': clarification_requests,
        'pending_count':          clarification_requests.filter(status='Pending').count(),
        'page_title':             'Clarification Requests',
    }
    return render(request, 'complaints/clarification_list.html', context)


@login_required
def respond_clarification(request, clarification_id):
    """Student or Faculty responds to a clarification request."""
    if request.user.role not in ['Student', 'Faculty', 'HOD']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    clarification = get_object_or_404(
        ClarificationRequest,
        id=clarification_id,
        target_user=request.user,
    )

    complaint    = clarification.finding.investigation.complaint
    investigator = clarification.finding.submitted_by

    if clarification.status == 'Responded':
        messages.info(request, 'You have already responded to this request.')
        return redirect('clarification_list')

    if request.method == 'POST':
        form = ClarificationResponseForm(request.POST)
        if form.is_valid():
            clarification.response_text = form.cleaned_data['response_text']
            clarification.responded_by  = request.user
            clarification.responded_at  = timezone.now()
            clarification.status        = 'Responded'
            clarification.save()

            finding       = clarification.finding
            all_responded = True

            if finding.needs_student_clarification:
                student_req = ClarificationRequest.objects.filter(
                    finding=finding, request_type='Student'
                ).first()
                if not student_req or student_req.status != 'Responded':
                    all_responded = False

            if finding.needs_faculty_statement:
                faculty_req = ClarificationRequest.objects.filter(
                    finding=finding, request_type='Faculty'
                ).first()
                if not faculty_req or faculty_req.status != 'Responded':
                    all_responded = False

            if all_responded:
                notif_msg = (
                    f'All clarification responses received for complaint '
                    f'"{complaint.subject}" ({complaint.tracking_id}). '
                    f'Please review responses and forward to the investigator.'
                )
            else:
                notif_msg = (
                    f'{request.user.full_name} has responded to the clarification for '
                    f'complaint "{complaint.subject}" ({complaint.tracking_id}). '
                    f'Waiting for remaining responses.'
                )

            create_notification(
                recipient=investigator,
                title=f'💬 Clarification Response Received — {complaint.tracking_id}',
                message=notif_msg,
                notification_type='complaint',
                link=f'/complaints/investigator/clarification/{finding.id}/responses/',
            )

            create_notification(
                recipient=finding.investigation.assigned_by,
                title=f'💬 Clarification Response — {complaint.tracking_id}',
                message=f'{request.user.full_name} has responded to the clarification for complaint "{complaint.subject}".',
                notification_type='complaint',
                link=f'/complaints/hod/handle/{complaint.id}/',
            )

            messages.success(request, 'Your response has been submitted.')
            return redirect('clarification_list')
    else:
        form = ClarificationResponseForm()

    context = {
        'clarification': clarification,
        'complaint':     complaint,
        'form':          form,
        'page_title':    'Respond to Clarification Request',
    }
    return render(request, 'complaints/respond_clarification.html', context)


@login_required
def view_clarification_responses(request, finding_id):
    """Investigator or HOD views all clarification responses."""
    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    finding        = get_object_or_404(InvestigationFinding, id=finding_id)
    clarifications = ClarificationRequest.objects.filter(finding=finding)
    all_responded  = clarifications.exists() and all(
        c.status == 'Responded' for c in clarifications
    )

    context = {
        'finding':        finding,
        'complaint':      finding.investigation.complaint,
        'clarifications': clarifications,
        'all_responded':  all_responded,
        'page_title':     'Clarification Responses',
    }
    return render(request, 'complaints/view_clarification_responses.html', context)


@login_required
def hod_forward_to_investigator(request, finding_id):
    """HOD forwards all clarification responses to the investigator."""
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied.')
        return redirect('login')

    finding        = get_object_or_404(InvestigationFinding, id=finding_id)
    complaint      = finding.investigation.complaint
    investigator   = finding.submitted_by
    clarifications = ClarificationRequest.objects.filter(finding=finding)

    if request.method == 'POST':
        response_summary = ''
        for c in clarifications:
            party = 'Student' if c.request_type == 'Student' else 'Accused Faculty'
            response_summary += f'\n--- {party} Response ---\n{c.response_text or "(no response)"}\n'

        create_notification(
            recipient=investigator,
            title=f'📋 Clarification Responses Ready — {complaint.tracking_id}',
            message=(
                f'HOD {request.user.full_name} has forwarded all clarification responses '
                f'for complaint "{complaint.subject}" ({complaint.tracking_id}).\n\n'
                f'Please review and submit your final verdict.\n'
                f'{response_summary}'
            ),
            notification_type='complaint',
            link=f'/complaints/investigator/clarification/{finding.id}/responses/',
        )

        messages.success(request, f'Responses forwarded to {investigator.full_name}.')

    return redirect('handle_complaint', complaint_id=complaint.id)


@login_required
def my_clarifications(request):
    """Student or Faculty sees all clarification requests sent to them."""
    if request.user.role not in ['Student', 'Faculty']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    clarifications = ClarificationRequest.objects.filter(
        target_user=request.user
    ).order_by('-created_at')

    context = {
        'clarifications': clarifications,
        'pending_count':  clarifications.filter(status='Pending').count(),
        'page_title':     'My Clarification Requests',
    }
    return render(request, 'complaints/my_clarifications.html', context)


@login_required
def hod_view_clarification_responses(request, complaint_id):
    """HOD views all clarification responses for a complaint."""
    if request.user.role != 'HOD':
        messages.error(request, 'Access denied.')
        return redirect('login')

    complaint = get_object_or_404(Complaint, id=complaint_id)

    try:
        investigation  = complaint.investigation
        clarifications = ClarificationRequest.objects.filter(
            finding__investigation=investigation
        ).order_by('-created_at')
    except ComplaintInvestigation.DoesNotExist:
        investigation  = None
        clarifications = []

    context = {
        'complaint':      complaint,
        'investigation':  investigation,
        'clarifications': clarifications,
        'page_title':     f'Clarification Responses — {complaint.tracking_id}',
    }
    return render(request, 'complaints/hod_clarification_responses.html', context)