# ISAC Portal — Django

A functional Django/MySQL implementation of the Integrated Student Activity & Clearance Portal for DMMMSU–NLUC CSBO.

## Stack
- Django 5.2
- MySQL
- HTML/CSS/JavaScript
- html5-qrcode for browser camera scanning
- qrcode/Pillow
- openpyxl for Excel
- ReportLab for PDF
- Lucide icons + Chart.js

## Setup on Windows

1. Install Python 3.12+ and MySQL.
2. Create the database:
   `mysql -u root -p < schema.sql`
3. Create and activate a virtual environment:
   `python -m venv venv`
   `venv\Scripts\activate`
4. Install packages:
   `pip install -r requirements.txt`
5. Configure database variables (optional if using defaults):
   - DB_NAME=isac_portal
   - DB_USER=root
   - DB_PASSWORD=your_password
   - DB_HOST=127.0.0.1
   - DB_PORT=3306
6. Run migrations:
   `python manage.py makemigrations`
   `python manage.py migrate`
7. Load demo data:
   `python manage.py seed_demo`
8. Start:
   `python manage.py runserver`
9. Open:
   http://127.0.0.1:8000/

## Demo accounts
- Student: `student1` / `Student12345!`
- Officer: `officer1` / `Officer12345!`
- Admin: `admin` / `Admin12345!`

## Important QR note
The digital ID page displays a QR generated from the student's unique UUID token. The scanner validates the token against the database. Camera scanning requires browser permission and normally HTTPS on deployed mobile environments.

## Modules
Student: dashboard, digital ID, event calendar, activities, clearance, announcements.
Officer: dashboard, events, QR scanner, attendance, fines, clearance, announcements, reports.
Admin: Django admin plus user listing.

## Security
Django CSRF protection, password hashing, ORM parameterization, route-level role checks, unique attendance constraints, transactions around attendance and points, and audit logs are included. For production, set DEBUG=0, a strong SECRET_KEY, HTTPS, secure cookies, proper ALLOWED_HOSTS, and a managed MySQL account.

## Testing checklist
- Login: student/officer/admin
- QR scan: valid token, duplicate token, invalid token
- Manual student-ID fallback
- Automatic participation point credit
- Clearance progress
- Fine records
- Event CRUD
- Announcement CRUD
- Report filters
- Excel/PDF export
- Light/dark mode
- Mobile responsive scanner
