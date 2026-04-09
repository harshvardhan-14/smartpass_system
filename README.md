# Smart Gate Pass System

A comprehensive visitor management system for residential societies and offices built with Django, featuring dynamic resident search, OTP authentication, and complete visitor lifecycle management.

## 🚀 Features

### Core Features
✅ **Dynamic Resident Search** - Smart search with filtering by building name and flat number  
✅ **Visitor Registration** - Security guard registers visitor with photo upload  
✅ **OTP Authentication** - Automatic OTP sent to resident via SMS  
✅ **Gate Pass Generation** - Digital pass with unique ID and QR code  
✅ **Entry/Exit Tracking** - Complete visitor lifecycle management  
✅ **Visitor History** - Comprehensive visitor records with filtering  
✅ **Photo Upload** - Capture visitor photos via camera or upload  

### User Roles & Interfaces
✅ **Security Guard Interface** - Register visitors, verify OTP, manage entry/exit  
✅ **Resident Dashboard** - View pending visitors, approve/reject requests  
✅ **Admin Panel** - Complete system management and reporting  
✅ **Role-Based Access** - Secure authentication and authorization  

### Advanced Features
✅ **Real-time Search** - Instant resident filtering as you type  
✅ **Visitor Statistics** - Track frequent and recent visitors  
✅ **Multi-criteria Filtering** - Filter by date, status, resident, purpose  
✅ **Password Reset** - Secure password recovery with OTP verification  
✅ **Profile Management** - Upload and manage profile photos  
✅ **Audit Logging** - Complete activity tracking  

## 🛠 Tech Stack

- **Backend**: Django 4.2+ with Django REST Framework
- **Frontend**: Bootstrap 5 + HTML5/CSS3/JavaScript
- **Database**: MySQL/PostgreSQL support
- **Authentication**: Django built-in auth system
- **OTP Service**: Twilio SMS integration
- **File Upload**: Django file handling with image processing
- **Security**: CSRF protection, password hashing, input validation

## 📋 Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL Server or PostgreSQL
- Twilio Account (for SMS OTP)
- Git

### Step-by-Step Setup

1. **Clone the Repository**
```bash
git clone https://github.com/harshvardhan-14/smartpass_system.git
cd smartpass_system
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
copy .env.example .env

# Edit .env and fill in your details:
# - TWILIO_ACCOUNT_SID
# - TWILIO_AUTH_TOKEN
# - TWILIO_PHONE_NUMBER
# - Database credentials
```

5. **Create Database**
```bash
# For MySQL
mysql -u root -p
> CREATE DATABASE smartpass_db;
> EXIT;

# Or use PostgreSQL
createdb smartpass_db
```

6. **Run Migrations**
```bash
python manage.py makemigrations
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

## 🎯 Usage Guide

### For Security Guard
1. **Register** at `/accounts/register/guard/`
2. **Login** at `/accounts/login/`
3. **Access Dashboard** at `/visitors/guard-dashboard/`
4. **Register Visitor** at `/visitors/register/`
   - Use dynamic resident search
   - Upload visitor photo
   - OTP automatically sent to resident
5. **Verify OTP** at `/visitors/verify-otp/<visitor_id>/`
6. **Generate Gate Pass** with QR code
7. **Mark Exit** when visitor leaves

### For Resident
1. **Register** at `/accounts/register/resident/`
2. **Login** at `/accounts/login/`
3. **View Dashboard** at `/visitors/resident-dashboard/`
4. **Manage Visitors** - Approve/reject pending requests
5. **View History** - Complete visitor records
6. **Update Profile** - Manage personal information

### For Admin
1. **Access Admin Panel** at `/admin/`
2. **Manage Users** - Residents, security guards
3. **View Reports** - Visitor statistics and analytics
4. **System Settings** - Configure application

## 🏗 Project Structure

```
smartpass_system/
├── config/                 # Django project settings
│   ├── settings.py        # Project configuration
│   ├── urls.py            # Main URL routing
│   ├── wsgi.py            # WSGI configuration
│   └── asgi.py            # ASGI configuration

├── accounts/              # User management app
│   ├── models.py          # User, Resident, SecurityGuard models
│   ├── views.py           # Authentication, profile management
│   ├── forms.py           # User registration forms
│   ├── urls.py            # Account URLs
│   ├── admin.py           # Admin configuration
│   └── decorators.py      # Custom decorators

├── visitors/             # Visitor management app
│   ├── models.py          # Visitor, OTP, GatePass models
│   ├── views.py           # Visitor registration, OTP verification
│   ├── forms.py           # Visitor registration forms
│   ├── urls.py            # Visitor URLs
│   ├── services.py        # OTP service implementation
│   └── admin.py           # Visitor admin configuration

├── templates/             # HTML templates
│   ├── base.html          # Base template with navigation
│   ├── home.html          # Landing page
│   ├── login.html         # Login page
│   ├── register_visitor.html  # Visitor registration with search
│   ├── register_guard.html     # Security guard registration
│   ├── register_resident.html  # Resident registration
│   ├── guard_dashboard.html     # Security guard interface
│   ├── resident_dashboard.html   # Resident interface
│   ├── verify_otp.html     # OTP verification page
│   ├── visitor_history.html # Visitor history with filtering
│   └── forgot_password.html    # Password reset

├── static/                # Static files
│   ├── css/              # Custom CSS
│   ├── js/               # JavaScript files
│   └── images/           # Static images

├── media/                 # User uploads
│   ├── visitor_photos/     # Visitor photo uploads
│   ├── guard_photos/      # Security guard photos
│   └── resident_photos/   # Resident photos

├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables
├── .env.example          # Example environment file
└── README.md             # This file
```

## 🗄 Database Models

### User Models
- **CustomUser** - Extended user model with user types
- **Resident** - Resident profile with building/flat details
- **SecurityGuard** - Security guard profile with shift info

### Visitor Management
- **Visitor** - Complete visitor information with photos
- **OTP** - OTP verification with expiration
- **VisitorHistory** - Complete visitor lifecycle tracking
- **GatePass** - Digital gate pass with QR codes

### Supporting Models
- **PasswordResetOTP** - Secure password reset functionality
- **ActivityLog** - Complete audit trail

## 🌐 Key Features Deep Dive

### Dynamic Resident Search
- **Smart Filtering**: Search by building name or flat number
- **Real-time Results**: Instant filtering as you type
- **Visitor Statistics**: Shows frequent and recent visitors
- **Visual Indicators**: Badges for popular residents
- **Mobile Friendly**: Responsive design for all devices

### Photo Upload System
- **Camera Capture**: Direct camera access via browser
- **File Upload**: Traditional file upload option
- **Image Validation**: File type and size validation
- **Secure Storage**: Organized media directory structure

### OTP System
- **Twilio Integration**: Reliable SMS delivery
- **Secure Generation**: Random 6-digit codes
- **Expiration**: 5-minute validity
- **Rate Limiting**: Prevent abuse
- **Multiple Attempts**: 3 maximum attempts

### Security Features
- **CSRF Protection**: Enabled by default
- **Password Hashing**: Django's secure password handling
- **Input Validation**: Comprehensive form validation
- **Role-Based Access**: Secure user permissions
- **Audit Logging**: Complete activity tracking

## 📱 API Endpoints

### Authentication
- `GET/POST /accounts/login/` - User login
- `GET/POST /accounts/register/guard/` - Security guard registration
- `GET/POST /accounts/register/resident/` - Resident registration
- `GET/POST /accounts/forgot-password/` - Password reset

### Visitor Management
- `GET/POST /visitors/register/` - Register new visitor
- `GET/POST /visitors/verify-otp/<visitor_id>/` - OTP verification
- `GET /visitors/api/search-residents/` - Dynamic resident search API
- `GET /visitors/guard-dashboard/` - Security guard dashboard
- `GET /visitors/resident-dashboard/` - Resident dashboard
- `GET /visitors/visitor-history/` - Visitor history with filtering

### Admin & Management
- `GET/POST /admin/` - Django admin interface
- `GET /accounts/user-profile/` - User profile management
- `GET/POST /accounts/edit-profile/` - Profile editing

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Database Configuration
DB_NAME=smartpass_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Django Configuration
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Twilio Setup
1. **Create Twilio Account** - Visit https://www.twilio.com
2. **Get Phone Number** - Purchase or get a trial number
3. **Update .env** - Add credentials to environment file
4. **Test SMS** - Verify OTP delivery

## 🔒 Security Considerations

⚠️ **Important Security Notes:**

1. **Production Settings**
   - Set `DEBUG = False` in production
   - Change `SECRET_KEY` from default
   - Use `ALLOWED_HOSTS` properly

2. **Database Security**
   - Use strong database passwords
   - Enable SSL for database connections
   - Regular database backups

3. **File Upload Security**
   - Validate file types and sizes
   - Secure media directory permissions
   - Scan uploaded files for malware

4. **OTP Security**
   - Use secure random number generation
   - Implement rate limiting
   - Log OTP attempts

5. **Web Security**
   - Enable HTTPS in production
   - Use secure session cookies
   - Implement proper CORS policies

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test accounts
python manage.py test visitors

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Test Features
- User authentication and authorization
- Visitor registration workflow
- OTP generation and verification
- Dynamic resident search
- Photo upload functionality
- Form validation

## 🐛 Troubleshooting

### Common Issues

**OTP not sending?**
- Check Twilio credentials in .env
- Verify phone number format (+country_code)
- Check Twilio account balance
- Review Twilio console logs

**Database connection error?**
- Ensure database server is running
- Check DB credentials in .env
- Verify database exists
- Check firewall settings

**Photo upload not working?**
- Check media directory permissions
- Verify file size limits
- Check disk space
- Review Django settings

**Dynamic search not working?**
- Check JavaScript console for errors
- Verify API endpoint accessibility
- Check network requests
- Ensure user is authenticated

### Development Issues

**Port already in use?**
```bash
python manage.py runserver 8080
```

**Migration errors?**
```bash
python manage.py migrate --fake-initial
python manage.py migrate
```

**Static files not loading?**
```bash
python manage.py collectstatic
```

## 📈 Performance Optimization

### Database Optimization
- Use `select_related()` and `prefetch_related()`
- Add database indexes for frequently queried fields
- Optimize queries with proper filtering

### Frontend Optimization
- Minify CSS and JavaScript
- Use browser caching
- Optimize image sizes
- Implement lazy loading

### Server Optimization
- Use production web server (Gunicorn/Nginx)
- Enable compression
- Implement caching strategies
- Monitor server resources

## 🚀 Deployment

### Production Setup
1. **Server Requirements**
   - Ubuntu 20.04+ or CentOS 8+
   - Python 3.8+
   - MySQL/PostgreSQL
   - Nginx/Apache
   - SSL Certificate

2. **Deployment Steps**
   ```bash
   # Clone repository
   git clone https://github.com/harshvardhan-14/smartpass_system.git
   
   # Setup virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Configure environment
   cp .env.example .env
   # Edit .env with production settings
   
   # Run migrations
   python manage.py migrate
   
   # Collect static files
   python manage.py collectstatic
   
   # Setup Gunicorn
   gunicorn config.wsgi:application
   
   # Configure Nginx
   # Setup SSL certificate
   ```

## 🤝 Contributing

### How to Contribute
1. **Fork** the repository
2. **Create** a feature branch
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit** your changes
   ```bash
   git commit -m 'Add amazing feature'
   ```
4. **Push** to the branch
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Create** a Pull Request

### Contribution Guidelines
- Follow PEP 8 for Python code
- Write meaningful commit messages
- Add tests for new features
- Update documentation
- Ensure all tests pass

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

### Getting Help
- **Documentation**: Read this README thoroughly
- **Issues**: Check existing GitHub issues
- **Questions**: Create a new GitHub issue
- **Django Docs**: https://docs.djangoproject.com/
- **Twilio Docs**: https://www.twilio.com/docs

### Contact
- **GitHub**: https://github.com/harshvardhan-14/smartpass_system
- **Email**: [Your email for support]

## 📊 Changelog

### Version 1.0.0 (Current Release)
- ✅ Complete visitor management system
- ✅ Dynamic resident search with filtering
- ✅ OTP-based authentication
- ✅ Photo upload functionality
- ✅ Role-based access control
- ✅ Visitor history and reporting
- ✅ Password reset functionality
- ✅ Mobile-responsive design
- ✅ Security best practices
- ✅ Production-ready configuration

### Upcoming Features
- 🔄 Real-time notifications
- 📊 Advanced analytics dashboard
- 📱 Mobile app integration
- 🔐 Two-factor authentication
- 📧 Email notifications
- 🌐 Multi-language support

---

**Built with ❤️ by Harshvardhan**

**🚀 Live Repository**: https://github.com/harshvardhan-14/smartpass_system

**⭐ If you find this project useful, give it a star!**
