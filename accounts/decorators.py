from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from functools import wraps
from .models import Admin

def admin_required(view_func):
    """
    Decorator to ensure user is authenticated and is an admin
    """
    @wraps(view_func)
    @login_required(login_url='accounts:login')
    def _wrapped_view(request, *args, **kwargs):
        # Check if user is admin
        if not request.user.is_authenticated or request.user.user_type != 'admin':
            return redirect('home')
        
        # Try to get admin profile
        try:
            admin_user = Admin.objects.get(user=request.user)
        except Admin.DoesNotExist:
            return redirect('home')
        
        # Add admin_user to request for easy access
        request.admin_user = admin_user
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
