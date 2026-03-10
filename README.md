# Student Recruiter Connection

A full-featured job board platform built with Django that connects job seekers (students) with recruiters. The platform supports job postings, applications with status tracking, candidate search, skill-based recommendations, messaging, notifications, and admin moderation.

## Tech Stack

- **Backend:** Django 5.2.5 (Python)
- **Database:** SQLite3
- **Frontend:** Django Templates, HTML5, CSS3, vanilla JavaScript
- **External APIs:** Nominatim/OpenStreetMap (geocoding), Gmail SMTP (email notifications)

## Features

### Job Seekers
- **Profile management** &mdash; headline, summary, location, skills, education, experience, and external links with per-section visibility controls
- **Job search** &mdash; full-text search with filters for location, work type, salary range, skills, distance (geolocation), and visa sponsorship
- **Applications** &mdash; quick-apply or detailed cover letter; track status from Applied through Interview to Offer/Accepted/Rejected
- **Recommendations** &mdash; skill-based job recommendations ranked by match score
- **Messaging** &mdash; in-platform messages and direct emails to recruiters

### Recruiters
- **Job posting** &mdash; create and manage jobs with required/nice-to-have skills, compensation details, and auto-geocoded locations
- **Application management** &mdash; review applications, update statuses, view applicant profiles, export to CSV
- **Candidate search** &mdash; search candidates by name, location, and skills; save searches for reuse
- **Saved search notifications** &mdash; get notified when new candidates match saved search criteria
- **Candidate recommendations** &mdash; view ranked candidates per job based on skill matching

### Admin / Moderation
- Custom admin dashboard with job moderation (remove/restore/close)
- Job reporting system (spam, inappropriate, fake, discriminatory)
- User management with role-based filtering
- CSV data export for jobs, applications, and users

## Project Structure

```
job_board/
├── manage.py
├── job_board/          # Django project settings & root URL config
├── accounts/           # Custom User model (JOB_SEEKER / RECRUITER), messaging
├── profiles/           # Job seeker profiles, skills, education, experience
├── jobs/               # Job CRUD, applications, candidate search, notifications, geocoding, admin
├── recommended/        # Skill-based recommendation engine
├── templates/          # HTML templates (base, accounts, profiles, jobs, recommended, admin)
└── static/             # CSS stylesheet
```

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/ethan-ignatius/StudentRecruiterConnection.git
cd StudentRecruiterConnection/job_board

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install django requests

# Apply database migrations
python manage.py migrate

# Load demo data
python manage.py loaddata ./dummy_jobs.json
```

### Running the Server

```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### Demo Accounts

| Username    | Role      | Password           |
|-------------|-----------|-------------------|
| seeker1     | Job Seeker | `Hellothere142857` |
| seeker2     | Job Seeker | `Hellothere142857` |
| recruiter1  | Recruiter  | `Hellothere142857` |
| recruiter2  | Recruiter  | `Hellothere142857` |

### Create an Admin Account

```bash
python manage.py createsuperuser
```

Access the admin panel at [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).

### Email Notifications (Optional)

To enable email features (job report alerts, candidate match notifications), set the following environment variables:

```bash
export EMAIL_HOST_USER="your-email@gmail.com"
export EMAIL_HOST_PASSWORD="your-gmail-app-password"
```

### Reset Data

```bash
# Option 1: Flush the database
python manage.py flush

# Option 2: Delete and recreate
rm db.sqlite3
python manage.py migrate
python manage.py loaddata ./dummy_jobs.json
```

## Key URL Routes

| Path | Description |
|------|-------------|
| `/` | Home page |
| `/accounts/signup/` | User registration |
| `/login/` | Login |
| `/profiles/me/` | My profile (job seeker) |
| `/jobs/` | Job search |
| `/jobs/post/` | Post a new job (recruiter) |
| `/jobs/my-jobs/` | My posted jobs (recruiter) |
| `/jobs/my-applications/` | My applications (job seeker) |
| `/jobs/candidates/` | Candidate search (recruiter) |
| `/recommended/` | Recommended jobs / candidates |
| `/jobs/notifications/` | Saved search notifications |
| `/admin/` | Admin panel |
