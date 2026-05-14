# complaints/utils.py

from django.db.models import Count, Q
from .models import Complaint
from feedback.models import CourseAssignment
from difflib import SequenceMatcher
import re


def similarity_score(string1, string2):
    """Calculate similarity score between two strings (0-1)"""
    return SequenceMatcher(None, string1.lower(), string2.lower()).ratio()


def get_faculty_complaints_summary(faculty_user):
    """
    Get all complaints against a specific faculty across all courses
    Returns: Dictionary with grouped and summarized complaints
    """
    
    # Get all complaints against this faculty
    complaints = Complaint.objects.filter(
        faculty_concerned=faculty_user,
        complaint_type='Faculty'
    ).select_related('student', 'faculty_concerned', 'assigned_to')
    
    # Get all courses taught by this faculty
    faculty_courses = CourseAssignment.objects.filter(
        faculty=faculty_user
    ).select_related('course')
    
    # Group complaints by course
    complaints_by_course = {}
    for assignment in faculty_courses:
        course = assignment.course
        course_complaints = complaints.filter(
            student__department=course.department
        )
        if course_complaints.exists():
            complaints_by_course[course] = course_complaints
    
    # Include complaints without course association
    unassigned_complaints = complaints.filter(
        ~Q(student__department__in=[a.course.department for a in faculty_courses])
    )
    
    return {
        'faculty': faculty_user,
        'total_complaints': complaints.count(),
        'complaints_by_course': complaints_by_course,
        'unassigned_complaints': unassigned_complaints,
        'all_complaints': complaints,
    }


def group_similar_complaints(complaints, similarity_threshold=0.6):
    """
    Group complaints with similar subjects/descriptions
    Returns: List of complaint groups with similarity info
    """
    
    grouped = []
    processed_ids = set()
    
    for complaint in complaints:
        if complaint.id in processed_ids:
            continue
        
        # Find similar complaints
        similar_group = {
            'primary': complaint,
            'similar_complaints': [],
            'similarity_scores': [],
            'count': 1
        }
        
        for other_complaint in complaints:
            if other_complaint.id == complaint.id or other_complaint.id in processed_ids:
                continue
            
            # Compare subject and description
            subject_similarity = similarity_score(complaint.subject, other_complaint.subject)
            desc_similarity = similarity_score(complaint.description, other_complaint.description)
            overall_similarity = (subject_similarity + desc_similarity) / 2
            
            if overall_similarity >= similarity_threshold:
                similar_group['similar_complaints'].append(other_complaint)
                similar_group['similarity_scores'].append(overall_similarity)
                similar_group['count'] += 1
                processed_ids.add(other_complaint.id)
        
        processed_ids.add(complaint.id)
        grouped.append(similar_group)
    
    # Sort by group size (most complaints first)
    grouped.sort(key=lambda x: x['count'], reverse=True)
    
    return grouped


def get_complaint_statistics(complaints):
    """
    Calculate statistics for a set of complaints
    Returns: Dictionary with various statistics
    """
    
    if not complaints.exists():
        return {
            'total': 0,
            'by_status': {},
            'by_priority': {},
            'by_type': {},
            'anonymous_count': 0,
            'resolved_count': 0,
            'pending_count': 0,
            'average_time_to_resolution': None,
        }
    
    stats = {
        'total': complaints.count(),
        'by_status': dict(complaints.values('status').annotate(count=Count('id')).values_list('status', 'count')),
        'by_priority': dict(complaints.values('priority').annotate(count=Count('id')).values_list('priority', 'count')),
        'by_type': dict(complaints.values('complaint_type').annotate(count=Count('id')).values_list('complaint_type', 'count')),
        'anonymous_count': complaints.filter(is_anonymous=True).count(),
        'resolved_count': complaints.filter(status='Resolved').count(),
        'pending_count': complaints.filter(status='Pending').count(),
        'under_investigation': complaints.filter(status='Under Investigation').count(),
    }
    
    # Calculate average resolution time for resolved complaints
    resolved_complaints = complaints.filter(status='Resolved', resolved_at__isnull=False)
    if resolved_complaints.exists():
        total_time = sum([
            (c.resolved_at - c.submitted_at).total_seconds() 
            for c in resolved_complaints
        ])
        avg_seconds = total_time / resolved_complaints.count()
        stats['average_time_to_resolution'] = f"{int(avg_seconds / 86400)} days"
    
    return stats


def get_top_complaint_subjects(complaints, limit=5):
    """
    Get the most common complaint subjects
    Returns: List of most frequent subjects
    """
    
    subject_counts = {}
    for complaint in complaints:
        subject = complaint.subject.strip()
        if subject not in subject_counts:
            subject_counts[subject] = {'count': 0, 'complaints': []}
        subject_counts[subject]['count'] += 1
        subject_counts[subject]['complaints'].append(complaint)
    
    # Sort by frequency
    sorted_subjects = sorted(
        subject_counts.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )
    
    return sorted_subjects[:limit]


def get_department_complaint_comparison(faculty_user, department=None):
    """
    Compare complaints for faculty in a specific department
    Returns: Comparison data with other faculty
    """
    
    if not department:
        department = faculty_user.department
    
    # Get all faculty in the department
    from users.models import User
    faculty_in_dept = User.objects.filter(
        role='Faculty',
        department=department
    )
    
    comparison_data = []
    for faculty in faculty_in_dept:
        complaints = Complaint.objects.filter(
            faculty_concerned=faculty,
            complaint_type='Faculty'
        )
        
        comparison_data.append({
            'faculty': faculty,
            'total_complaints': complaints.count(),
            'resolved': complaints.filter(status='Resolved').count(),
            'pending': complaints.filter(status='Pending').count(),
            'high_priority': complaints.filter(priority__in=['High', 'Urgent']).count(),
        })
    
    # Sort by total complaints
    comparison_data.sort(key=lambda x: x['total_complaints'], reverse=True)
    
    return comparison_data
