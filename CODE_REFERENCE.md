# 📝 Code Structure & Functions Reference

## Core Functions in `utils.py`

### 1. `similarity_score(string1, string2)`
**Purpose:** Calculate similarity between two strings
**Algorithm:** SequenceMatcher from difflib
**Returns:** Float between 0 and 1 (0 = completely different, 1 = identical)
**Usage:**
```python
score = similarity_score("unfair grading", "grading is unfair")
# Returns: 0.95 (95% similar)
```

---

### 2. `get_faculty_complaints_summary(faculty_user)`
**Purpose:** Get all complaints for a specific faculty
**Returns:** Dictionary with:
```python
{
    'faculty': User object,
    'total_complaints': 15,
    'complaints_by_course': {Course: QuerySet, ...},
    'unassigned_complaints': QuerySet,
    'all_complaints': QuerySet,
}
```
**Usage:**
```python
summary = get_faculty_complaints_summary(faculty_obj)
print(summary['total_complaints'])  # 15
```

---

### 3. `group_similar_complaints(complaints, similarity_threshold=0.6)`
**Purpose:** Group complaints with similar subjects/descriptions
**Parameters:**
- `complaints`: QuerySet of complaints
- `similarity_threshold`: Float (0-1) for grouping threshold
**Returns:** List of grouped complaints:
```python
[
    {
        'primary': Complaint object,
        'similar_complaints': [Complaint, Complaint, ...],
        'similarity_scores': [0.75, 0.68, ...],
        'count': 3,
    },
    ...
]
```
**Logic:**
1. Compares each complaint subject + description
2. If similarity >= threshold, groups together
3. Sorts groups by size (largest first)

**Example:**
```python
groups = group_similar_complaints(all_complaints, similarity_threshold=0.55)
for group in groups:
    print(f"{group['count']} similar complaints found")
```

---

### 4. `get_complaint_statistics(complaints)`
**Purpose:** Calculate comprehensive statistics
**Returns:** Dictionary with:
```python
{
    'total': 15,
    'by_status': {'Pending': 3, 'Resolved': 10, ...},
    'by_priority': {'High': 4, 'Medium': 8, ...},
    'by_type': {'Faculty': 12, 'HOD': 3},
    'anonymous_count': 2,
    'resolved_count': 10,
    'pending_count': 3,
    'under_investigation': 2,
    'average_time_to_resolution': '5 days',
}
```
**Calculations:**
- Counts by grouping and aggregating
- Time calculation: (resolved_at - submitted_at) average
- All in days

**Usage:**
```python
stats = get_complaint_statistics(all_complaints)
print(stats['by_status'])  # {'Pending': 3, 'Resolved': 10}
```

---

### 5. `get_top_complaint_subjects(complaints, limit=5)`
**Purpose:** Find most common complaint subjects
**Returns:** List of tuples:
```python
[
    ('Unfair Grading', {'count': 5, 'complaints': [...]},
    ('Rude Behavior', {'count': 4, 'complaints': [...]},
    ...
]
```
**Logic:**
1. Groups complaints by exact subject text
2. Counts occurrences
3. Sorts by frequency
4. Returns top N (default 5)

**Usage:**
```python
subjects = get_top_complaint_subjects(all_complaints, limit=5)
for subject, data in subjects:
    print(f"{subject}: {data['count']} occurrences")
```

---

### 6. `get_department_complaint_comparison(faculty_user, department=None)`
**Purpose:** Compare one faculty against all others in department
**Returns:** List of dictionaries:
```python
[
    {
        'faculty': User object,
        'total_complaints': 20,
        'resolved': 15,
        'pending': 3,
        'high_priority': 2,
    },
    {
        'faculty': User object,
        'total_complaints': 15,  # Ranked 2nd
        'resolved': 10,
        'pending': 3,
        'high_priority': 2,
    },
    ...
]
```
**Logic:**
1. Gets all faculty in department
2. Counts complaints per faculty
3. Calculates metrics per faculty
4. Sorts by total complaints (highest first)

**Usage:**
```python
comparison = get_department_complaint_comparison(faculty_obj)
for faculty_data in comparison:
    print(f"{faculty_data['faculty'].name}: {faculty_data['total_complaints']}")
```

---

## Views in `views.py`

### 1. `faculty_complaint_summary(request)`
**HTTP Method:** GET, POST
**Permission:** HOD only (`@login_required`)
**Parameters:**
- `faculty_id`: (query param) Selected faculty ID

**Logic Flow:**
1. Check if user is HOD
2. Get all faculty in HOD's department
3. If `faculty_id` provided:
   - Get that faculty
   - Get summary data
   - Group similar complaints
   - Calculate statistics
   - Get top subjects
   - Get department comparison
4. Render template with context

**Template Context:**
```python
{
    'page_title': 'Faculty Complaint Analysis',
    'faculty_list': QuerySet,
    'selected_faculty': User or None,
    'summary_data': dict,
    'statistics': dict,
    'similar_groups': list,
    'top_subjects': list,
    'comparison_data': list,
}
```

**Template:** `faculty_complaint_summary.html`

---

### 2. `faculty_course_wise_complaints(request, faculty_id)`
**HTTP Method:** GET
**Permission:** HOD only
**Parameters:**
- `faculty_id`: URL parameter (required)

**Logic Flow:**
1. Get faculty by ID
2. Check if in HOD's department
3. Get all CourseAssignments for faculty
4. For each course:
   - Get complaints for that course
   - Count by status/priority
   - Collect in data structure
5. Sort by total complaints
6. Render template

**Template Context:**
```python
{
    'page_title': f'Course-wise Complaints - {faculty.name}',
    'faculty': User,
    'course_complaint_data': [
        {
            'course': Course,
            'assignment': CourseAssignment,
            'total_complaints': 5,
            'pending': 2,
            'resolved': 3,
            'investigating': 0,
            'high_priority': 1,
            'complaints': QuerySet,
        },
        ...
    ],
    'total_complaints': 15,
}
```

**Template:** `faculty_course_wise_complaints.html`

---

### 3. `similar_complaints_detail(request, faculty_id, group_index)`
**HTTP Method:** GET
**Permission:** HOD only
**Parameters:**
- `faculty_id`: URL parameter
- `group_index`: URL parameter (0-based index)

**Logic Flow:**
1. Get faculty and verify department
2. Get summary for that faculty
3. Group all complaints
4. Get group at specific index
5. Return group data

**Template Context:**
```python
{
    'page_title': 'Similar Complaints Detail',
    'faculty': User,
    'group': {
        'primary': Complaint,
        'similar_complaints': [Complaint, ...],
        'similarity_scores': [0.75, 0.68],
        'count': 3,
    },
    'group_index': 1,
    'total_groups': 5,
}
```

**Template:** `similar_complaints_detail.html`

---

## URL Routing in `urls.py`

```python
# Main Dashboard
path('hod/faculty-complaint-summary/', 
     views.faculty_complaint_summary, 
     name='faculty_complaint_summary')

# Course Breakdown
path('hod/faculty-course-wise/<int:faculty_id>/', 
     views.faculty_course_wise_complaints, 
     name='faculty_course_wise_complaints')

# Similar Details
path('hod/similar-complaints/<int:faculty_id>/<int:group_index>/', 
     views.similar_complaints_detail, 
     name='similar_complaints_detail')
```

---

## Template Structure

### `faculty_complaint_summary.html`
**Sections:**
1. Header with title
2. Faculty selection form
3. Selected faculty info card
4. Statistics row (6 cards)
5. Status & Priority breakdown
6. Top complaint subjects
7. Similar complaints groups
8. Department comparison table
9. Action buttons

**Key Variables Used:**
- `selected_faculty` - Current faculty
- `statistics` - Stats dict
- `similar_groups` - List of groups
- `top_subjects` - Top 5 subjects
- `comparison_data` - Ranking list
- `faculty_list` - For dropdown

---

### `faculty_course_wise_complaints.html`
**Sections:**
1. Header with faculty name
2. Faculty info card
3. For each course:
   - Course card header
   - Statistics for course
   - Complaint table

**Key Variables Used:**
- `faculty` - Faculty object
- `course_complaint_data` - List of course data
- `total_complaints` - Sum of all

---

### `similar_complaints_detail.html`
**Sections:**
1. Header with title
2. Navigation (previous/next groups)
3. Primary complaint card
4. Similar complaints list
5. Pattern analysis summary
6. Recommended actions
7. Back button

**Key Variables Used:**
- `group` - Current group dict
- `faculty` - Faculty object
- `group_index` - Current index
- `total_groups` - Total groups count

---

## Database Queries

### Query 1: Get all complaints for faculty
```python
Complaint.objects.filter(faculty_concerned=faculty, complaint_type='Faculty')
```

### Query 2: Get by course
```python
Complaint.objects.filter(
    faculty_concerned=faculty,
    student__department=course.department
)
```

### Query 3: Statistics by status
```python
complaints.values('status').annotate(count=Count('id'))
```

### Query 4: Get with related data
```python
complaints.select_related('student', 'faculty_concerned', 'assigned_to')
```

### Query 5: Get courses for faculty
```python
CourseAssignment.objects.filter(faculty=faculty).select_related('course')
```

---

## Data Flow Diagram

```
User Selects Faculty
        ↓
View: faculty_complaint_summary()
        ↓
get_faculty_complaints_summary()
        ├→ Get all complaints
        ├→ Group by course
        └→ Return summary
        ↓
group_similar_complaints()
        └→ Compare subjects
        └→ Group by similarity
        └→ Return groups
        ↓
get_complaint_statistics()
        ├→ Count by status
        ├→ Count by priority
        └→ Return stats
        ↓
get_top_complaint_subjects()
        └→ Count subjects
        └→ Sort by frequency
        └→ Return top 5
        ↓
get_department_complaint_comparison()
        ├→ Get all faculty
        ├→ Count complaints each
        └→ Return ranking
        ↓
Render Template with all data
        ↓
User sees Dashboard
```

---

## Key Features of Code

### 1. **Security**
- HOD-only access with `@login_required`
- Department scoping (can't access other departments)
- Safe URL parameters (no direct field access)

### 2. **Performance**
- Uses `select_related()` to reduce queries
- Uses `annotate()` and `Count()` for aggregation
- Queries at database level (not Python)

### 3. **Reusability**
- Utility functions can be used elsewhere
- Functions are independent and composable
- Easy to test individual functions

### 4. **Maintainability**
- Clear function names and purposes
- Good documentation and comments
- Separated concerns (utils, views, templates)

### 5. **Extensibility**
- Easy to add more statistics
- Easy to adjust thresholds
- Easy to customize templates

---

## Example Code Usage

### Using in Admin Command
```python
from complaints.utils import get_faculty_complaints_summary
from users.models import User

faculty = User.objects.get(id=5)
summary = get_faculty_complaints_summary(faculty)
print(f"Total: {summary['total_complaints']}")
```

### Using in Django Shell
```python
python manage.py shell

from complaints.utils import get_complaint_statistics
from complaints.models import Complaint

complaints = Complaint.objects.all()
stats = get_complaint_statistics(complaints)
print(stats)
```

### Using in API View
```python
from django.http import JsonResponse
from complaints.utils import group_similar_complaints

complaints = Complaint.objects.filter(faculty_concerned=faculty)
groups = group_similar_complaints(list(complaints))
return JsonResponse({'groups': groups})
```

---

## Customization Examples

### Add Email Notification
```python
# In similar_complaints_detail, after finding pattern:
if group['count'] > 5:
    send_email_to_hod(
        faculty=faculty,
        pattern_count=group['count']
    )
```

### Add Caching
```python
from django.core.cache import cache

key = f'complaints_{faculty_id}'
data = cache.get(key)
if not data:
    data = get_faculty_complaints_summary(faculty)
    cache.set(key, data, 3600)  # 1 hour
```

### Add Pagination
```python
from django.core.paginator import Paginator

paginator = Paginator(all_complaints, 20)
page_complaints = paginator.get_page(request.GET.get('page'))
```

---

## Testing Examples

### Test Similarity Score
```python
from complaints.utils import similarity_score

assert similarity_score("hello", "hello") == 1.0
assert similarity_score("hello", "world") < 0.5
assert 0 <= similarity_score("abc", "xyz") <= 1
```

### Test Grouping
```python
from complaints.utils import group_similar_complaints

complaints = [complaint1, complaint2, ...]
groups = group_similar_complaints(complaints, 0.55)
assert len(groups) > 0
assert groups[0]['count'] > 0
```

### Test View Access
```python
from django.test import TestCase, Client

class FacultyComplaintTest(TestCase):
    def test_hod_access(self):
        client = Client()
        client.login(username='hod', password='pass')
        response = client.get('/complaints/hod/faculty-complaint-summary/')
        assert response.status_code == 200
```

---

This complete code reference explains every function, view, and template in the feature!
