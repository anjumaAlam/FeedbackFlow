# Faculty Complaint Analysis Feature - Implementation Guide

## Overview

This new feature allows HODs (Heads of Department) to analyze complaints against specific faculty members in their department. It provides:

1. **Complaint Summary Dashboard** - Overview of all complaints for a faculty
2. **Pattern Detection** - Groups similar complaints together to identify systemic issues
3. **Statistical Analysis** - Breakdown by status, priority, and complaint type
4. **Course-wise Analysis** - See which courses have the most complaints
5. **Department Comparison** - Compare faculty complaint records across the department
6. **Similarity Grouping** - Identify recurring issues with percentage accuracy

---

## Step-by-Step Implementation

### Step 1: Understand the File Structure

**Files Added/Modified:**

```
complaints/
├── utils.py (NEW)                    # Utility functions for analysis
├── views.py (MODIFIED)               # Added 3 new views
├── urls.py (MODIFIED)                # Added 3 new URL patterns
└── templates/complaints/
    ├── faculty_complaint_summary.html (NEW)
    ├── faculty_course_wise_complaints.html (NEW)
    └── similar_complaints_detail.html (NEW)
```

### Step 2: What Each File Does

#### **A. `complaints/utils.py` - Analysis Functions**

Contains 6 main utility functions:

1. **`similarity_score(string1, string2)`**
   - Calculates how similar two texts are (0-1 scale)
   - Uses Python's SequenceMatcher
   - Returns higher value for more similar text

2. **`get_faculty_complaints_summary(faculty_user)`**
   - Gets all complaints against a specific faculty
   - Groups complaints by course
   - Returns organized complaint data

3. **`group_similar_complaints(complaints, similarity_threshold=0.6)`**
   - Groups complaints with similar subjects/descriptions
   - Default threshold: 60% similarity
   - Returns sorted groups by frequency

4. **`get_complaint_statistics(complaints)`**
   - Calculates comprehensive statistics
   - Includes: total count, status breakdown, priority breakdown, resolution time
   - Returns dictionary with all stats

5. **`get_top_complaint_subjects(complaints, limit=5)`**
   - Identifies most frequently occurring complaint subjects
   - Returns top 5 by default
   - Useful for pattern identification

6. **`get_department_complaint_comparison(faculty_user, department=None)`**
   - Compares one faculty against all others in department
   - Shows relative complaint frequency
   - Helps identify outliers

#### **B. `complaints/views.py` - New Views**

3 new views added:

1. **`faculty_complaint_summary(request)`**
   - Main dashboard view
   - HOD selects faculty member
   - Displays all analysis data
   - Shows similar complaint groups

2. **`faculty_course_wise_complaints(request, faculty_id)`**
   - Detailed breakdown by course
   - Shows complaints for each course taught
   - Lists individual complaints per course

3. **`similar_complaints_detail(request, faculty_id, group_index)`**
   - Detailed view of one similarity group
   - Shows primary complaint and all similar ones
   - Includes analysis summary and recommendations

#### **C. `complaints/urls.py` - Routes**

Three new URL patterns:

```python
path('hod/faculty-complaint-summary/', views.faculty_complaint_summary, 
     name='faculty_complaint_summary'),
     
path('hod/faculty-course-wise/<int:faculty_id>/', views.faculty_course_wise_complaints, 
     name='faculty_course_wise_complaints'),
     
path('hod/similar-complaints/<int:faculty_id>/<int:group_index>/', 
     views.similar_complaints_detail, 
     name='similar_complaints_detail'),
```

#### **D. Templates - User Interface**

1. **faculty_complaint_summary.html**
   - Faculty selection dropdown
   - Statistics cards (total, pending, resolved, etc.)
   - Status and priority breakdown tables
   - Top complaint subjects
   - Similar complaint groups
   - Department faculty comparison

2. **faculty_course_wise_complaints.html**
   - Faculty info card
   - One card per course taught
   - Statistics for each course
   - Sortable complaint table per course

3. **similar_complaints_detail.html**
   - Primary complaint display
   - All similar complaints list
   - Pattern analysis summary
   - Recommended actions
   - Navigation between groups

---

## How to Use the Feature

### Access the Feature

1. **Login as HOD** in your department
2. **Navigate to:** `/complaints/hod/faculty-complaint-summary/`
   - Or add a link in the HOD dashboard

### Using the Dashboard

1. **Select Faculty Member**
   - Use dropdown to select a faculty member from your department
   - Click "Analyze" button

2. **View Statistics**
   - See total complaints, pending, resolved, under investigation
   - View average resolution time
   - Check anonymous complaint percentage

3. **Analyze Patterns**
   - Scroll to "Top Complaint Subjects" section
   - Identifies most common issues
   - Shows how many times each subject appears

4. **View Similar Complaints Group**
   - Scroll to "Grouped Similar Complaints" section
   - Red cards indicate multiple similar complaints
   - Click "View Details" for deeper analysis

5. **Compare with Department**
   - See how this faculty compares to others
   - Check complaint frequency ranking
   - View resolved vs pending ratio

6. **Course-wise Breakdown**
   - Click "View Course-wise Breakdown" button
   - See complaints organized by course taught
   - Identify problematic courses

7. **Individual Complaint Details**
   - Click "View Details" in similar complaints group
   - See primary complaint and all related complaints
   - Get recommended actions for the pattern

---

## Example Workflow

### Scenario: HOD Analyzes Faculty Complaints

**Step 1: Access Dashboard**
```
Go to: /complaints/hod/faculty-complaint-summary/
```

**Step 2: Select Faculty**
- Select "Prof. John Smith" from dropdown
- Click "Analyze"

**Step 3: View Summary**
- Total: 15 complaints
- Pending: 3
- Resolved: 10
- Under Investigation: 2

**Step 4: Check for Patterns**
- 5 complaints about "Unfair Grading"
- 4 complaints about "Rude Behavior"
- 3 complaints about "Missing Classes"

**System automatically groups similar complaints:**
- Group 1: 5 similar complaints about grading (60% similarity)
- Group 2: 4 similar complaints about behavior (65% similarity)

**Step 5: Investigate Group**
- Click on "5 Similar Complaints" group
- View all 5 grading complaints together
- See pattern analysis recommending investigation

**Step 6: Take Action**
- Escalate serious patterns to formal investigation
- Schedule faculty counseling
- Increase monitoring

---

## Key Features Explained

### 1. Similarity Score

**How it works:**
- Compares complaint subjects and descriptions
- Uses sequence matching algorithm
- Score ranges from 0 (completely different) to 1 (identical)
- Default threshold: 0.55 (55% similarity)

**Example:**
```
Complaint 1: "Faculty doesn't explain concepts clearly"
Complaint 2: "Hard to understand the teaching"
Similarity: ~65% - Will be grouped together
```

### 2. Statistical Breakdown

Shows:
- **By Status:** Pending, Under Investigation, Resolved, Escalated
- **By Priority:** Low, Medium, High, Urgent
- **Anonymous Complaints:** Count of anonymous reports
- **Average Resolution Time:** Days to resolve complaint

### 3. Top Complaint Subjects

Identifies patterns by:
- Counting identical or similar subjects
- Sorting by frequency
- Showing number of occurrences
- Marking patterns as "Critical" if > 3 complaints

### 4. Department Comparison

Compares selected faculty with all others showing:
- Total complaints (ranking)
- Resolved complaints
- Pending complaints
- High priority complaints

---

## Database Queries Used

The feature uses these Django ORM queries:

```python
# Get all complaints for faculty
Complaint.objects.filter(faculty_concerned=faculty)

# By course
Complaint.objects.filter(
    faculty_concerned=faculty,
    student__department=course.department
)

# By status
Complaint.objects.filter(status='Resolved').count()

# Aggregate statistics
complaints.values('status').annotate(count=Count('id'))

# Related objects
.select_related('student', 'faculty_concerned', 'assigned_to')
```

---

## Customization Options

### Change Similarity Threshold

In `utils.py`, modify the function call:

```python
# Current: 0.55 (55% similarity)
similar_groups = group_similar_complaints(all_complaints, similarity_threshold=0.55)

# More strict (only very similar): 0.75
similar_groups = group_similar_complaints(all_complaints, similarity_threshold=0.75)

# More lenient (catch all similarities): 0.40
similar_groups = group_similar_complaints(all_complaints, similarity_threshold=0.40)
```

### Modify Statistics to Include

Edit `get_complaint_statistics()` in `utils.py` to add/remove fields:

```python
stats = {
    'total': complaints.count(),
    # Add custom metrics here
    'avg_resolution_days': 15,  # Example
    'unresolved_critical': complaints.filter(
        status='Pending', 
        priority='Urgent'
    ).count(),
}
```

### Top Subjects Limit

Change the limit:

```python
# Current: top 5
top_subjects = get_top_complaint_subjects(all_complaints, limit=5)

# Show top 10
top_subjects = get_top_complaint_subjects(all_complaints, limit=10)
```

---

## Integration with Existing System

### How It Integrates

1. **Uses Existing Models:**
   - `Complaint` model
   - `CourseAssignment` model
   - `User` model (faculty)

2. **Respects Existing Permissions:**
   - Only HOD can access
   - Can only view own department faculty

3. **Follows Existing Patterns:**
   - Same template base (`users/base.html`)
   - Same styling and layout
   - Same authentication decorator

### Adding Navigation Link

To add a link in HOD dashboard, edit your HOD template:

```html
<a href="{% url 'faculty_complaint_summary' %}" class="btn btn-primary">
    <i class="fas fa-chart-bar"></i> Complaint Analysis
</a>
```

---

## Performance Considerations

### Database Optimization

- Uses `select_related()` to reduce queries
- Uses `annotate()` and `Count()` for aggregation
- Filters at database level, not Python

### Caching (Optional Enhancement)

For departments with many complaints, add caching:

```python
from django.core.cache import cache

cache.set('faculty_complaints_' + str(faculty_id), data, timeout=3600)
cached_data = cache.get('faculty_complaints_' + str(faculty_id))
```

### Pagination (Optional Enhancement)

For large complaint lists, add pagination:

```python
from django.core.paginator import Paginator

paginator = Paginator(all_complaints, 20)
page_complaints = paginator.get_page(request.GET.get('page', 1))
```

---

## Troubleshooting

### Issue: No complaints showing

**Solution:**
1. Check if faculty has role='Faculty'
2. Verify complaints have complaint_type='Faculty'
3. Ensure complaints are in same department as HOD

### Issue: Similarity grouping not working

**Solution:**
1. Lower the similarity threshold
2. Verify complaint subjects are entering database
3. Check text encoding (should be UTF-8)

### Issue: Slow performance

**Solution:**
1. Add database indexes on frequently queried fields
2. Implement caching for statistics
3. Add pagination for large complaint lists

---

## Testing the Feature

### Manual Test Cases

1. **Create test complaints:**
```python
# Create 5 similar complaints
for i in range(5):
    Complaint.objects.create(
        student=student,
        complaint_type='Faculty',
        faculty_concerned=faculty,
        subject='Unfair Grading',
        description='The grading is very unfair and biased',
        status='Pending'
    )
```

2. **Access the feature:**
   - Go to: `/complaints/hod/faculty-complaint-summary/`
   - Select your test faculty
   - Verify all 5 complaints are grouped

3. **Check statistics:**
   - Should show 5 total
   - Should show 5 pending
   - Should show 0 resolved

4. **Test department comparison:**
   - Should show your faculty in ranking
   - Should compare against other faculty

---

## API Endpoints

| URL | Method | Permission | Description |
|-----|--------|-----------|-------------|
| `/complaints/hod/faculty-complaint-summary/` | GET | HOD | Main dashboard |
| `/complaints/hod/faculty-complaint-summary/` | POST | HOD | Select faculty |
| `/complaints/hod/faculty-course-wise/<id>/` | GET | HOD | Course breakdown |
| `/complaints/hod/similar-complaints/<id>/<index>/` | GET | HOD | Similar group details |

---

## Summary

This feature provides HODs with powerful tools to:
- ✅ Identify patterns in faculty complaints
- ✅ Find systemic issues quickly
- ✅ Compare faculty performance
- ✅ Make data-driven decisions
- ✅ Improve faculty accountability
- ✅ Enhance institutional quality

All with a user-friendly, intuitive interface!
