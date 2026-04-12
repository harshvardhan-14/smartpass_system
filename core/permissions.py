"""
Custom DRF permission classes for Gate Pass System.
"""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow access only to users with user_type='admin'."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type == 'admin'
        )


class IsResident(BasePermission):
    """Allow access only to users with user_type='resident'."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type == 'resident'
        )


class IsSecurityGuard(BasePermission):
    """Allow access only to security guards (user_type in ['security', 'guard'])."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type in ('security', 'guard')
        )


class IsAdminOrReadOnly(BasePermission):
    """Admin can write; authenticated users can read."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.user_type == 'admin'


class IsOwnerOrAdmin(BasePermission):
    """Object-level: owner or admin can access."""

    def has_object_permission(self, request, view, obj):
        if request.user.user_type == 'admin':
            return True
        # For resident objects
        if hasattr(obj, 'resident') and hasattr(request.user, 'resident'):
            return obj.resident == request.user.resident
        # For user objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user


class IsSecurityGuardOrAdmin(BasePermission):
    """Allow security guards and admins."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type in ('security', 'guard', 'admin')
        )


class IsResidentOrAdmin(BasePermission):
    """Allow residents and admins."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type in ('resident', 'admin')
        )
