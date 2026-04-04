# feedback/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count

from .models import Feedback, Course, FeedbackResponse
from .forms import FeedbackSubmissionForm, FeedbackResponseForm

# STUDENT VIEWS


@login_required
def submit_feedback(request):
    """Student submits feedback for a course"""

    if request.user.role != 'Student':
        messages.error(request, 'Only students can submit feedback.')
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = FeedbackSubmissionForm(request.POST, user=request.user)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.student = request.user
            feedback.save()

            messages.success(
                request,
                f'Feedback submitted successfully for {feedback.course.course_code}!'
            )
            return redirect('my_feedback')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeedbackSubmissionForm(user=request.user)

    context = {
        'form': form,
        'page_title': 'Submit Course Feedback'
    }
    return render(request, 'feedback/submit_feedback.html', context)


@login_required
def my_feedback(request):
    """Student views their submitted feedback"""

    if request.user.role != 'Student':
        messages.error(request, 'Access denied.')
        return redirect('login')

    feedback_list = Feedback.objects.filter(student=request.user).select_related('course', 'course__faculty')

    context = {
        'feedback_list': feedback_list,
        'page_title': 'My Feedback'
    }
    return render(request, 'feedback/my_feedback.html', context)


@login_required
def feedback_detail(request, feedback_id):
    """View detailed feedback with response"""

    feedback = get_object_or_404(Feedback, id=feedback_id)

    # Check permission
    if request.user.role == 'Student' and feedback.student != request.user:
        messages.error(request, 'You can only view your own feedback.')
        return redirect('my_feedback')

    context = {
        'feedback': feedback,
        'page_title': 'Feedback Detail'
    }
    return render(request, 'feedback/feedback_detail.html', context)



# FACULTY VIEWS


@login_required
def faculty_feedback_list(request):
    """Faculty views all feedback for their courses"""

    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('login')


    feedback_list = Feedback.objects.filter(
        course__faculty=request.user
    ).select_related('course', 'student').order_by('-submitted_at')


    total_feedback = feedback_list.count()
    pending_response = feedback_list.filter(status='Pending').count()


    avg_ratings = feedback_list.aggregate(
        avg_teaching=Avg('teaching_rating'),
        avg_content=Avg('content_rating'),
        avg_communication=Avg('communication_rating')
    )

    context = {
        'feedback_list': feedback_list,
        'total_feedback': total_feedback,
        'pending_response': pending_response,
        'avg_teaching': round(avg_ratings['avg_teaching'] or 0, 1),
        'avg_content': round(avg_ratings['avg_content'] or 0, 1),
        'avg_communication': round(avg_ratings['avg_communication'] or 0, 1),
        'page_title': 'My Course Feedback'
    }
    return render(request, 'feedback/faculty_feedback_list.html', context)


@login_required
def respond_to_feedback(request, feedback_id):
    """Faculty responds to student feedback"""

    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('login')

    feedback = get_object_or_404(Feedback, id=feedback_id)


    if feedback.course.faculty != request.user:
        messages.error(request, 'You can only respond to feedback for your own courses.')
        return redirect('faculty_feedback_list')


    if hasattr(feedback, 'response'):
        messages.info(request, 'You have already responded to this feedback.')
        return redirect('faculty_feedback_list')

    if request.method == 'POST':
        form = FeedbackResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.feedback = feedback
            response.faculty = request.user
            response.save()


            feedback.status = 'Responded'
            feedback.reviewed_at = timezone.now()
            feedback.save()

            messages.success(request, 'Response submitted successfully!')
            return redirect('faculty_feedback_list')
    else:
        form = FeedbackResponseForm()

    context = {
        'form': form,
        'feedback': feedback,
        'page_title': 'Respond to Feedback'
    }
    return render(request, 'feedback/respond_to_feedback.html', context)


@login_required
def mark_feedback_reviewed(request, feedback_id):
    """Faculty marks feedback as reviewed without response"""

    if request.user.role not in ['Faculty', 'HOD']:
        messages.error(request, 'Access denied.')
        return redirect('login')

    feedback = get_object_or_404(Feedback, id=feedback_id)

    if feedback.course.faculty != request.user:
        messages.error(request, 'Access denied.')
        return redirect('faculty_feedback_list')

    feedback.status = 'Reviewed'
    feedback.reviewed_at = timezone.now()
    feedback.save()

    messages.success(request, 'Feedback marked as reviewed.')
    return redirect('faculty_feedback_list')
