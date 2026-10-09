# Examination Management Portal (EMP)

An enterprise-grade Academic Examination Management Portal built with **Flask**, **Jinja2**, **Bootstrap 5**, and **SQLite**. It enables Educational Institutions to schedule courses, automate student slot bookings, coordinate faculty examiners, and record rubric-based evaluations without relying on spreadsheets or manual coordination.

---

## 🚀 Key Highlights & Architectural Compliance

1. **Backend Framework**: Built strictly using **Flask 3.1** and **Flask-SQLAlchemy**.
2. **Frontend UI**: Built with **Jinja2 templating**, HTML5, CSS3, and **Bootstrap 5.3**.
3. **Pure Server-Side Execution (No JS for Core Features)**:
   - All forms, validations, slot bookings, cancellations, rubric evaluations, phase overrides, and queries submit via standard HTTP `GET`/`POST` requests and server-side redirects with flash messages.
4. **Programmatic SQLite Database Creation**:
   - The SQLite database (`examination_portal.db`) is generated 100% programmatically via SQLAlchemy model code.
   - Initialized and seeded via `seed_data.py`. No manual database creation tools (like DB Browser) are used.
5. **Pre-existing Administrator Superuser**:
   - Pre-seeded in the database (`admin / admin123`). Public registration for the administrator role is strictly prohibited.
6. **Robust Role-Based Access Control (RBAC)**:
   - Enforced across `Admin`, `Examiner`, and `Student` roles using Flask-Login and role wrappers.
7. **Official Scorecard & Print Optimization**:
   - Students can view detailed criterion-by-criterion marks and qualitative examiner remarks, and print or export an official academic scorecard via browser print stylesheet (`@media print`).

---

## 👥 Role Capabilities

### 1. Administrator (Superuser)
- **Pre-existing superuser** in the database.
- **Real-Time Dashboard**: Total counts for courses, examinations, examiners, students, exam slots, and bookings.
- **Course Management**: Create, edit, search, and delete academic courses.
- **Examination Management**: Create, edit, and configure examination types (*Viva*, *Practical*, *Project Demo*, *Assessment*), maximum marks, and durations.
- **Examination Timelines & Phase Control**:
  - Configure start and end dates for slot creation and student bookings.
  - One-click administrative phase overrides (*Draft*, *Open Slot Creation*, *Open Slot Booking*, *Closed*, *Completed*).
- **Rubrics Management**: Define evaluation criteria, max marks, weightage, and guidelines per examination.
- **Examiner Approval Workflow**: View pending examiner registrations; approve, reject, deactivate, or reactivate faculty accounts.
- **Slots & Roster Oversight**: View all examination slots across all examiners with capacity indicators.
- **Reassign Examiner**: Change assigned examiner for a slot in exceptional situations.
- **Reschedule Bookings**: Move student bookings to alternative available slots of the same examination.
- **Global Search**: Unified search for students, examiners, examinations, and bookings by Name or ID.

### 2. Examiner (Faculty)
- **Self-Registration & Approval Gate**: Self-registers; dashboard is blocked until approved by the Administrator.
- **Examiner Dashboard**: View assigned examinations, created examination slots, booked student counts, and pending evaluations.
- **Slot Creation**: Create examination time slots during the sanctioned slot creation window.
- **Slot Modification**: Edit or delete slots before students begin booking.
- **Student Roster**: Inspect students booked for each slot (roll number, name, email, booking status).
- **Rubric-Based Evaluation**:
  - Grade candidate against each specific rubric criterion defined by the admin.
  - Automatically calculates total awarded marks.
  - Submit qualitative remarks and overall feedback.
  - **Strict Security Policy**: Examiners can evaluate **only** students booked into their own slots.

### 3. Student
- **Self-Registration & Instant Access**: Register with roll number, department, email, and password.
- **Student Dashboard**: Quick access to open examinations, available slots, upcoming appointments, and published scorecards.
- **Examination Directory**: Search and filter examinations by course code, name, or exam type.
- **Slot Booking**:
  - Book available slots during the booking window.
  - **Overbooking Prevention**: Real-time seat tracking auto-closes slots when capacity is reached.
  - **Duplicate Booking Prevention**: Prohibits a student from booking multiple slots for the same examination.
- **Cancellation**: Cancel bookings before the examination's booking deadline.
- **Booking History**: Track all current and past examination reservations.
- **Official Scorecard**: View published results, breakdown by rubric criteria, examiner comments, and printable transcript.
- **Profile Management**: Update full name, department, and contact information.

---

## 📂 Project Structure

```
Mad_1_project_in_ai/
├── app/
│   ├── __init__.py              # Application factory & error handlers
│   ├── config.py                # Database URI and secret configuration
│   ├── models.py                # SQLAlchemy Models (User, Course, Exam, Slot, Booking, etc.)
│   ├── auth/                    # Authentication Blueprint (login, register, logout)
│   ├── admin/                   # Administrator Blueprint (courses, exams, rubrics, examiners, etc.)
│   ├── examiner/                # Examiner Blueprint (slots, roster, rubric evaluation)
│   ├── student/                 # Student Blueprint (catalog, booking, scorecard, profile)
│   ├── api/                     # REST API Blueprint returning JSON endpoints
│   ├── static/
│   │   └── css/
│   │       └── custom.css       # Clean styling, badges, and print styles
│   └── templates/
│       ├── base.html            # Main Jinja2 layout with responsive navbar & alerts
│       ├── home.html            # Welcome landing page with credentials summary
│       ├── auth/                # Login, register_student, register_examiner
│       ├── admin/               # Admin dashboard, forms, rubrics, examiners, search, etc.
│       ├── examiner/            # Examiner dashboard, slot forms, student roster, evaluation
│       └── student/             # Student dashboard, catalog, slots, bookings, scorecard, profile
├── tests/
│   └── test_app.py              # Automated test suite (9 test cases covering RBAC & business logic)
├── requirements.txt             # Python dependencies
├── seed_data.py                 # Programmatic DB creator & initial data populator
├── run.py                       # Main application entry point
├── REPORT.md                    # 5-page submission project report
└── README.md                    # Documentation
```

---

## 🛠️ Installation & Setup Guide

### 1. Prerequisites
- Python 3.10+ installed on your local machine.

### 2. Setup Virtual Environment & Install Dependencies
Open your terminal in the project directory:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS / Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 3. Initialize Database Programmatically
Create the SQLite database schema and seed it with realistic test data:

```bash
python seed_data.py
```

### 4. Run the Web Application
```bash
python run.py
```

Open your web browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 🔑 Pre-Seeded Demo Credentials

| Role | Username | Password | Purpose / Notes |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Pre-existing superuser with full system authority |
| **Examiner** | `examiner1` | `examiner123` | Approved Faculty (Dr. Rajesh Kumar) |
| **Examiner** | `examiner2` | `examiner123` | Approved Faculty (Dr. Sunita Rao) |
| **Pending Examiner**| `pending_examiner`| `examiner123`| Pending approval to test Admin approval flow |
| **Student** | `student1` | `student123` | Has completed evaluation & downloadable scorecard |
| **Student** | `student2` | `student123` | Has active booking awaiting evaluation |

---

## 🧪 Running Automated Tests

To run the automated test suite verifying role-based access control, booking constraints, duplicate prevention, and API endpoints:

```bash
python -m unittest tests/test_app.py
```

---

## 🌐 REST API Endpoints

The portal includes clean JSON REST APIs for institutional system integration:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/courses` | List all active academic courses |
| `GET` | `/api/examinations` | List all examinations with timeline bounds |
| `GET` | `/api/examinations/<id>` | Examination details and associated rubrics |
| `GET` | `/api/examinations/<id>/slots` | List all slots created for an examination |
| `GET` | `/api/examiners` | List examiners and their approval status |
| `GET` | `/api/bookings` | List all booking records with evaluation status |
| `GET` | `/api/stats` | System aggregate statistics |
