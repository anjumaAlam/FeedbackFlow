# FeedbackFlow 🎓

FeedbackFlow is a comprehensive, multi-role Feedback and Complaint Management System designed for the **University of Asia Pacific (UAP)**. It provides a secure, transparent, and structured way for students, faculty, and administration to communicate, track issues, and improve the university environment.

---

## 🌟 Key Features

### 1. Multi-Role Authentication & Dashboards
The system supports distinct user roles, each with a tailored dashboard and specific permissions:
- **Student:** Submit feedback, file complaints, and track the status of their requests.
- **Faculty:** View feedback reports, investigate assigned complaints, and communicate with students.
- **HOD (Head of Department):** Oversee department feedback, assign investigators, and take final disciplinary action on complaints.
- **Admin & DAO:** Manage the entire system, escalate severe issues, and oversee facility maintenance.
- **Staff:** Receive assignments for physical infrastructure repairs.

### 2. Advanced Report Analysis & Analytics 📊
*Feature developed by the Core Team (Anjuma)*
FeedbackFlow includes a powerful analytics engine built with Plotly to visualize data:
- **Semester-wise Multi-Metric Comparison:** Generates dynamic grouped bar charts that compare average ratings (Teaching, Content, and Communication) side-by-side across different semesters.
- **KPI Tracking:** Real-time calculation of overall performance metrics for faculty members.
- **Visual Dashboards:** Easy-to-read graphical representations of feedback trends over time, helping the administration make data-driven decisions.

### 3. Transparent Complaint Management
- **Status Tracking:** Complaints transition through states: `Pending` -> `Under Investigation` -> `Findings Submitted` -> `Resolved` / `Escalated`.
- **Public Anonymized Log (FR 7.5):** A transparent, public bulletin board that lists recently resolved facility issues. This proves to students that action is being taken while strictly protecting privacy by keeping names hidden.
- **Departmental Routing:** Complaints are automatically routed to the correct HOD or Admin based on the department and severity.

### 4. Course Feedback
- Allows students to give detailed, structured ratings on teaching quality, course content, and communication.
- Supports both anonymous and named submissions.

### 5. Enhanced User Interface
- **Modern Login Experience:** Features a sleek dark-themed UI with custom toggleable password visibility (Eye Icon) to improve user accessibility.
- **Responsive Design:** Fully mobile-friendly interface built with Bootstrap 5 and custom CSS.

---

## 🛠️ Technology Stack

- **Backend Framework:** Django 6.0.5 (Python 3)
- **Database:** SQLite3 (Development) / PostgreSQL (Production Ready)
- **Frontend:** HTML5, Vanilla CSS, Bootstrap 5
- **Data Visualization:** Plotly.js
- **Icons:** Bootstrap Icons, SVG
- **Version Control:** Git & GitHub

---

## 🚀 Setup and Installation

Follow these steps to run FeedbackFlow on your local machine.

### Prerequisites
- Python 3.10+ installed
- Git installed
- `pip` package manager

### 1. Clone the Repository
```bash
git clone https://github.com/anjumaAlam/FeedbackFlow.git
cd FeedbackFlow
```

### 2. Create a Virtual Environment
```bash
python -m venv .venv
# Activate on Windows:
.venv\Scripts\activate
# Activate on Mac/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
# Note: Ensure Django 6.0.5 and Plotly are installed
pip install django plotly
```

### 4. Database Setup & Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Seed the Database (Optional)
To test the system with dummy data (like resolved facility complaints):
```bash
python seed_resolved_complaints.py
```

### 6. Run the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000` in your browser!

---

## 📁 Project Structure

```text
FeedbackFlow/
├── complaints/           # Handles complaint submission, routing, and investigation
├── feedback/             # Handles course registration and feedback forms
├── users/                # Custom User model, authentication, and Dashboards
├── feedbackflow/         # Core Django settings and configurations
├── seed_resolved_complaints.py # Database seeding script
└── manage.py             # Django execution script
```

---

## 🧑‍💻 Recent Developer Contributions
Significant modules successfully implemented:
1. **Report Analysis Engine:** Re-engineered the `feedback_analytics` view to process multi-trace Plotly charts for semester-by-semester comparison of teaching metrics.
2. **Public Anonymized Log:** Developed the `public_log` view and template to fulfill Functional Requirement 7.5, ensuring facility transparency.
3. **UI Enhancements:** Integrated interactive JavaScript password toggles and fixed contrast issues across the application.

---
*Developed for the University of Asia Pacific. All rights reserved.*
