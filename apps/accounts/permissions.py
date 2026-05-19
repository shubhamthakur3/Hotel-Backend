"""
Role-based permission classes for the Hotel Backend API.

These are used as DRF permission_classes on views to enforce
role-based access control.
"""

from rest_framework.permissions import BasePermission

from .models import UserRole


class IsAdmin(BasePermission):
    """Allows access only to users with the ADMIN role."""

    message = "Admin access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.has_role(UserRole.ADMIN)
        )


class IsHotelManager(BasePermission):
    """Allows access only to users with the HOTEL_MANAGER role."""

    message = "Hotel manager access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.has_role(UserRole.HOTEL_MANAGER)
        )


class IsGuest(BasePermission):
    """Allows access only to users with the GUEST role."""

    message = "Guest access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.has_role(UserRole.GUEST)
        )


class IsAdminOrManager(BasePermission):
    """Allows access to users with ADMIN or HOTEL_MANAGER role."""

    message = "Admin or hotel manager access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.has_role(UserRole.ADMIN)
                or request.user.has_role(UserRole.HOTEL_MANAGER)
            )
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: allows access only if the user
    owns the object or is an ADMIN.

    The view's queryset model must have a 'user' or 'owner' field.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.has_role(UserRole.ADMIN):
            return True

        # Check common ownership fields
        owner = getattr(obj, "user", None) or getattr(obj, "owner", None)
        return owner == request.user
