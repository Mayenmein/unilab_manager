# University Computer Laboratory Management System

## Table of Contents
1. Overview & Key Features
2. Role-Based Access Control
3. System Architecture & Prerequisites
4. Installation & Local Setup
5. Database Setup & Seeding
6. Running the Application
7. Core Workflows & Logic
8. Running Tests
9. Project Structure

---

## 1. Overview & Key Features

This project is a Django-based laboratory management platform for university computer labs. It is designed to coordinate two distinct layers of access and scheduling:

- Macro-level lab space locking by lecturers for scheduled class sessions.
- Micro-level workstation and seat reservations by students for enrolled course sessions.

The system enforces a fixed one-hour time-slot workflow, creates a clean resource hierarchy, and protects the integrity of room and seat scheduling through database-level validation and constraints.

### Core features

- **Two-tier resource hierarchy:**
  - Lab rooms are locked by lecturers using class bookings.
  - Individual workstations are reserved by students within those lab sessions.
- **Fixed 1-hour scheduling windows** via `TimeSlot` records.
- **Database-enforced atomic rules** to prevent race conditions, collisions, and duplicate reservations.
- **Student-only seat reservations** for active class sessions, validated against course enrollment.
- **Dual-path fault handling engine** for seat reports using `report_fault`.
- **Dynamic proximity-based reseating** using absolute seat-distance calculations.
- **Lecturer-driven class cancellation** that cascades into seat reservation cleanup.
- **Admin account approval gate:** New registrations require administrator activation before accounts can log in.
- **Full ticket lifecycle sync:** Admins or Maintenance staff can mark tickets as resolved, which automatically restores workstations to active status.
- **Bootstrap 5 interface** for student and lecturer dashboards.
- **Custom user roles** with role-based redirects and access control.

---

## 2. Role-Based Access Control

The project uses a custom `User` model in `accounts/models.py` with role-based access control.

### Student
- Role: `STUDENT`
- Can view the student dashboard.
- Can reserve available seats for labs tied to their enrolled courses.
- Can report faulty workstations.
- May be automatically reseated if the reported seat is theirs and an alternative seat is available.

### Lecturer
- Role: `LECTURER`
- Can create class bookings that lock a lab for a course at a specific date and time slot.
- Can cancel class bookings.
- Can manage scheduled lab sessions for their own courses.

### Maintenance Staff
- Role: `MAINTENANCE`
- Can be assigned maintenance tickets through the `MaintenanceTicket.assigned_to` field.
- Handles resolution workflows and hardware maintenance for workstation defects.

### Admin
- Role: `ADMIN`
- Has administrative privileges and access to the Django admin panel.
- **Account Approval Gate:** Reviews and activates newly registered user accounts (`is_active = True`) before they are permitted to log in.
- **Ticket Resolution:** Updates reported maintenance tickets to `RESOLVED` or `CLOSED`, which automatically returns fixed seats to the pool of operational workstations.
- Manages site data, lab capacities, and user roles from `/admin/`.

---

## 3. System Architecture & Prerequisites

### Architecture overview

The application is organized into three primary Django apps:

- `accounts/` — custom authentication and role model.
- `academics/` — course and enrollment logic.
- `labs/` — lab scheduling, seat reservations, faults, and maintenance tickets.

### Core domain model flow

- `Course` defines a taught subject and a lecturer owner.
- `CourseEnrollment` links a student to a course.
- `Lab` represents a physical lab room and auto-generates workstation seats based on its capacity.
- `Workstation` is the physical seat in a lab.
- `TimeSlot` stores fixed hourly scheduling blocks.
- `ClassBooking` locks a lab for a course at a specific date and time.
- `WorkstationReservation` reserves a specific seat for a student in that lab slot.
- `MaintenanceTicket` logs hardware issues and marks a workstation as under maintenance.

### Prerequisites

- Python 3.10+
- Django framework
- SQLite for local development (default configuration)
- PostgreSQL support for production-style deployments
- Bootstrap 5 for the UI layout and styling
- A virtual environment is recommended for local development

### Default project settings

The project currently uses SQLite in `unilab_manager/settings.py`:

- Database engine: `django.db.backends.sqlite3`
- Database file: `db.sqlite3`

This makes local setup simple while still keeping the project architecture compatible with PostgreSQL-based deployment.

---

## 4. Installation & Local Setup

### 1) Clone the repository

```bash
git clone https://github.com/Mayenmein/unilab_manager.git
cd unilab_manager
```

### 2) Create a virtual environment

```bash
python -m venv .venv
```

On Windows:

```powershell
.\.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

### 3) Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Note: the repository’s current `requirements.txt` is intentionally minimal; for a working local setup, you should ensure Django and any needed database driver are present, such as `Django` and `psycopg2-binary` if targeting PostgreSQL.

### 4) Environment configuration

The project currently runs with a local SQLite database and an inline insecure secret key in development. For a cleaner production-ready setup, create a `.env` file in the project root:

```env
DEBUG=True
SECRET_KEY=your-very-secret-key
DATABASE_URL=sqlite:///db.sqlite3
```

If you are using PostgreSQL instead of SQLite, you can set:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/unilab_manager
```

Then adapt `settings.py` to load these values using a package such as `python-dotenv` or `django-environ`.

---

## 5. Database Setup & Seeding

### Create and apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Seed default time-slot data

This project includes a custom management command:

```bash
python manage.py seed_labs
```

The seeder creates the fixed time-slot records used by the booking system, including the standard hourly blocks such as:

- Morning Slot 1: 08:00 - 10:00
- Morning Slot 2: 10:00 - 12:00
- Afternoon Slot 1: 12:00 - 14:00
- Afternoon Slot 2: 14:00 - 16:00

### Create an admin user

```bash
python manage.py createsuperuser
```

Follow the prompts to create the first admin account and access the Django admin dashboard.

---

## 6. Running the Application

Start the local development server:

```bash
python manage.py runserver
```

Then open the following pages in the browser:

- Student portal: http://127.0.0.1:8000/student/
- Lecturer portal: http://127.0.0.1:8000/lecturer/
- Registration: http://127.0.0.1:8000/accounts/register/
- Login: http://127.0.0.1:8000/accounts/login/
- Admin: http://127.0.0.1:8000/admin/

The root route redirects based on the logged-in role:

- Admin/staff -> `/admin/`
- Lecturer -> `/lecturer/`
- Student -> `/student/`

---

## 7. Core Workflows & Logic

### 7.1 User Registration & Admin Approval Flow

1. A new student or lecturer registers via `/accounts/register/`.
2. The account is created with `is_active = False`.
3. The user is redirected to a pending approval page informing them that account activation is required.
4. An Administrator logs into `/admin/`, reviews the user details, and activates the account (`is_active = True`).
5. Once activated, the user can log in and access their respective portal.

### 7.2 Administrative Academic & Facility Setup

To ensure operational order, establish system capacity, and prevent unauthorized scheduling:

1. **Lab Facility Creation:** An Administrator initializes physical `Lab` spaces in `/admin/` (configuring lab names and seat capacities), which automatically provisions the corresponding `Workstation` records for each room.
2. **Lecturer Course Assignment:** The Administrator creates `Course` records and assigns a specific activated `Lecturer` as the primary instructor for each module.
3. **Student Course Enrollment:** For system simplicity, the Administrator creates `CourseEnrollment` records, mapping active students to their assigned course modules.
4. **Prerequisite Enforcement:** Lecturers can only schedule class locks for courses explicitly assigned to them by the Admin, and students can only reserve seats for lab sessions tied to courses in which they are enrolled.

### 7.3 Lecture-Driven Lab Locking

Once assigned a course by the Admin, a lecturer creates a `ClassBooking` for a specific lab, course, date, and `TimeSlot`.

This lock is implemented at the lab level and ensures that a room cannot be double-booked during the same day and slot.

Key data integrity rules:

- `ClassBooking` uses `unique_together = ('lab', 'date', 'time_slot')`
- A lecturer must be assigned to the specific course they are booking for.
- A lab cannot be booked if it is inactive or closed.

### 7.4 Student Workstation Reservation Flow

Students reserve workstations only for active class-locked lab sessions tied to their enrolled courses.

Rules enforced in `WorkstationReservation.clean()`:

- Only students may create a reservation.
- A workstation must be available and the lab must be active.
- A student can reserve only one seat per slot per date.
- The seat must be within a lab whose course session is active for that time slot.
- The student must be enrolled in the corresponding course (assigned via `CourseEnrollment` by the Admin).

The data model also enforces:

- `unique_together = ('workstation', 'date', 'time_slot')`
- `UniqueConstraint(fields=['student', 'date', 'time_slot'])`

### 7.5 Fault Reporting and Dynamic Reseating (`report_fault`)

The `report_fault` workflow is a dual-path recovery engine that handles maintenance issues while preserving user assignments.

#### Path A: Active reservation on the reported workstation
When a student reports a fault on a workstation they are currently assigned to:

1. A `MaintenanceTicket` is created with status `OPEN`.
2. The workstation status automatically updates to `MAINTENANCE`.
3. The current reservation for that student/date/slot is identified.
4. The system computes the nearest alternative seat in the same lab and time block using absolute seat distance: `ABS(seat_number - faulty_seat_number)`.
5. The old reservation is deleted and replaced with a reservation on the closest available seat.

#### Path B: Unreserved or non-owned seat report
If the user is not currently assigned to that workstation:

- The ticket is created and workstation status changes to `MAINTENANCE`.
- No automatic reseat occurs.
- The user receives a standard thank-you notification.

### 7.6 Maintenance Ticket Lifecycle & Resolution

1. **Reporting:** When a fault ticket is created (`OPEN` / `IN_PROGRESS`), `MaintenanceTicket.save()` changes the workstation status to `MAINTENANCE`.
2. **Resolution:** An Admin or Maintenance Staff user resolves the hardware issue and sets the ticket status to `RESOLVED` or `CLOSED` in the Admin panel.
3. **Automatic Status Restoration:** `MaintenanceTicket.save()` checks if any other active tickets remain for that seat. If none exist, it automatically toggles the workstation back to `AVAILABLE`, instantly making it visible for future bookings.

### 7.7 Lecturer Cancellation and Cascading Cleanup

When a lecturer cancels a `ClassBooking`, the process runs within `transaction.atomic()`:

1. Find the class booking by lecturer and booking ID.
2. Delete all `WorkstationReservation` records tied to the same lab, date, and time slot.
3. Delete the class booking itself.
4. Return the lecturer to the dashboard with a confirmation message.

---

## 8. Running Tests

Run the project’s test suite for the lab and scheduling logic:

```bash
python manage.py test labs
```

The current tests cover:

- lecturer lab booking permissions
- student enrollment validation
- blocked seat reservations for unenrolled students
- room double-booking prevention
- maintenance ticket behavior

---

## 9. Project Structure

```text
unilab_manager/
├── academics/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── accounts/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── migrations/
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── labs/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── decorators.py
│   ├── management/
│   │   └── commands/
│   │       └── seed_labs.py
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_alter_lab_is_active.py
│   │   ├── 0003_timeslot_classbooking_workstationreservation.py
│   │   ├── 0004_maintenanceticket.py
│   │   └── 0005_workstationreservation_unique_student_reservation_per_slot.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── templates/
│   ├── base.html
│   ├── accounts/
│   │   ├── login.html
│   │   ├── pending_approval.html
│   │   └── register.html
│   └── labs/
│       ├── lecturer_dashboard.html
│       └── student_dashboard.html
├── unilab_manager/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── db.sqlite3
├── manage.py
├── requirements.txt
└── README.md
```

---

This project provides a practical example of a university lab scheduling system where physical lab scheduling, seat-level allocation, and maintenance workflows are all coordinated through a single Django application. It is well suited for academic use, internal operations, and demonstration of role-based scheduling in a constrained resource environment.

---
## Live Demo & Evaluator Credentials

* **Live Site:** [https://unilab.pythonanywhere.com](https://unilab.pythonanywhere.com)
* **Admin Panel:** [https://unilab.pythonanywhere.com/admin/](https://unilab.pythonanywhere.com/admin/)

### Evaluation Credentials
| Role | Username | Password |
| :--- | :--- | :--- |
| **Admin** | `admin@gmail.com` | `admin` |
| **Lecturer** | `lecturer_demo@gmail.com` | `LecturerPass2026!` |
| **Student** | `student_demo@gmail.com` | `StudentPass2026!` |