# Smart Gate Pass System with OTP Authentication

A comprehensive visitor management system for residential societies and offices using Django, REST APIs, and Twilio SMS for OTP-based verification.

## Features

✅ **Visitor Registration** - Security guard registers visitor details
✅ **OTP Authentication** - Automatic OTP sent to resident via SMS
✅ **Gate Pass Generation** - Digital pass with unique ID and QR code
✅ **Entry/Exit Tracking** - Record visitor entry and exit times
✅ **Visitor History** - View and filter visitor records
✅ **Role-Based Access** - Different interfaces for Security Guard, Resident, and Admin
✅ **Real-time Notifications** - Residents notified of visitors
✅ **REST APIs** - Built-in API endpoints for mobile apps

## Tech Stack

- **Backend**: Django 4.2+
- **Frontend**: Bootstrap 5 + HTML/CSS
- **Database**: MySQL/PostgreSQL
- **OTP Service**: Twilio SMS
- **REST API**: Django REST Framework
- **Authentication**: Django built-in auth system

## Installation and Setup

### Prerequisites
- Python 3.8+
- MySQL Server
- Twilio Account (for SMS OTP)

### Step-by-Step Setup

1. **Clone and Navigate to Project**
```bash
cd steeprise_project
```

2. **Create Virtual Environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Environment Variables**
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env and fill in your details:
# - TWILIO_ACCOUNT_SID
# - TWILIO_AUTH_TOKEN
# - TWILIO_PHONE_NUMBER
# - Database credentials
```

5. **Create Database**
```bash
# Create database in MySQL
mysql -u root
> CREATE DATABASE gatepass_db;
> EXIT;
```

6. **Run Migrations**
```bash
python manage.py migrate
```

7. **Create Superuser (Admin)**
```bash
python manage.py createsuperuser
```

8. **Start Development Server**
```bash
python manage.py runserver
```

Access the application at: `http://localhost:8000`

## Usage

### For Security Guard
1. Register as Security Guard at `/api/register/guard/`
2. Login to `/api/login/`
3. Go to Guard Dashboard `/api/guard/dashboard/`
4. Register visitor `/api/guard/register-visitor/`
5. OTP is automatically sent to resident
6. Verify OTP `/api/guard/verify-otp/<visitor_id>/`
7. Gate Pass generated with QR code
8. Mark exit when visitor leaves

### For Resident
1. Register as Resident at `/api/register/resident/`
2. Login to `/api/login/`
3. View pending visitors in Resident Dashboard `/api/resident/dashboard/`
4. Approve or reject visitor request
5. View visitor history `/api/resident/history/`

### For Admin
1. Access Django Admin at `/admin/`
2. Login with superuser credentials
3. Manage residents, security guards, and view all reports

## Project Structure

```
steeprise_project/
├── config/                 # Django project settings
│   ├── settings.py        # Project configuration
│   ├── urls.py            # Project URL routing
│   ├── wsgi.py            # WSGI configuration
│   └── asgi.py            # ASGI configuration
│
├── gatepass/              # Main Django app
│   ├── models.py          # Database models
│   ├── views.py           # View logic
│   ├── urls.py            # App URL routing
│   ├── forms.py           # Django forms
│   ├── serializers.py     # DRF serializers
│   ├── services.py        # Twilio OTP service
│   ├── admin.py           # Admin configuration
│   └── tests.py           # Unit tests
│
├── templates/             # HTML templates
│   ├── base.html          # Base template
│   ├── home.html          # Home page
│   ├── login.html         # Login page
│   ├── register_resident.html
│   ├── register_guard.html
│   ├── guard_dashboard.html
│   ├── resident_dashboard.html
│   ├── register_visitor.html
│   ├── verify_otp.html
│   ├── gate_pass_details.html
│   ├── mark_exit.html
│   └── visitor_history.html
│
├── static/                # Static files (CSS, JS, images)
├── media/                 # User uploads
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── .env.example           # Example env file
└── README.md              # This file
```

## Database Models

### Resident
- User (FK to User)
- Flat Number
- Phone Number
- Building Name
- Created At

### SecurityGuard
- User (FK to User)
- Employee ID
- Phone Number
- Shift (Morning/Evening/Night)
- Created At

### Visitor
- Visitor Name
- Mobile Number
- Purpose
- Resident (FK)
- Security Guard (FK)
- Identity Proof Type
- Identity Number
- Visitor Photo
- Entry Time
- Exit Time

### OTP
- Visitor (OneToOne)
- Resident (FK)
- OTP Code
- Is Verified
- Created At
- Expires At (5 minutes)
- Attempts (max 3)

### GatePass
- Visitor (OneToOne)
- Pass ID (unique)
- Resident (FK)
- Issue Time
- Valid Till (24 hours)
- Status (Active/Expired/Cancelled)
- QR Code

### VisitorHistory
- Visitor (FK)
- Resident (FK)
- Entry Time
- Exit Time
- Purpose
- Status (Approved/Rejected/Pending)
- Created At

## API Endpoints

### Authentication
- `POST /api/login/` - User login
- `POST /api/register/resident/` - Register resident
- `POST /api/register/guard/` - Register security guard

### Guard Operations
- `GET /api/guard/dashboard/` - Guard dashboard
- `POST /api/guard/register-visitor/` - Register new visitor
- `POST /api/guard/verify-otp/<visitor_id>/` - Verify OTP
- `GET /api/guard/gate-pass/<pass_id>/` - View gate pass
- `POST /api/guard/mark-exit/<visitor_id>/` - Mark visitor exit

### Resident Operations
- `GET /api/resident/dashboard/` - Resident dashboard
- `POST /api/resident/approve/<visitor_id>/` - Approve visitor
- `POST /api/resident/reject/<visitor_id>/` - Reject visitor
- `GET /api/resident/history/` - View visitor history

### REST API
- `GET /api/visitors/` - List all visitors
- `GET /api/residents/` - List all residents
- `GET /api/gatepasses/` - List all gate passes
- `GET /api/visitor-history/` - List visitor history
- `POST /api/verify-otp/` - API OTP verification

## Twilio Setup Guide

1. **Create Twilio Account**
   - Visit https://www.twilio.com/console
   - Sign up for free account
   - Get your Account SID and Auth Token

2. **Get Twilio Phone Number**
   - Go to Phone Numbers section
   - Get or buy a phone number
   - Format: +1234567890

3. **Update .env file**
   ```
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+your_phone_number
   ```

4. **Test OTP Delivery**
   - Register a visitor
   - Check if OTP SMS is received by resident

## Security Considerations

⚠️ **Important Security Notes:**

1. Change `SECRET_KEY` in production
2. Set `DEBUG = False` in production
3. Use environment variables for sensitive data
4. Implement HTTPS
5. Use CSRF protection (enabled by default)
6. Validate all user inputs
7. Hash passwords (Django handles this)
8. Use secure session cookies
9. Implement rate limiting for OTP requests
10. Regular database backups

## Testing

Run tests with:
```bash
python manage.py test
```

## Troubleshooting

### OTP not sending?
- Check Twilio credentials in .env
- Verify phone number format (+country_code format)
- Check Twilio account balance
- Review Twilio console logs

### Database connection error?
- Ensure MySQL server is running
- Check DB credentials in .env
- Verify database exists

### Migration errors?
- Delete db.sqlite3 if using SQLite
- Run: `python manage.py migrate`

### Port already in use?
- Use different port: `python manage.py runserver 8080`

## Contributing

Feel free to fork, modify, and improve this project!

## License

MIT License - feel free to use in your projects

## Support

For issues and questions, refer to Django documentation at https://docs.djangoproject.com/

## Changelog

### Version 1.0 (Initial Release)
- Basic visitor registration
- OTP-based verification
- Gate pass generation
- Entry/exit tracking
- Visitor history
- REST APIs
