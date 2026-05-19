"""
Custom User model for the Hotel Backend API.

Uses email as the primary login identifier instead of username.
Supports multiple roles: GUEST, HOTEL_MANAGER, ADMIN.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserRole:
    """User role constants."""

    GUEST = "GUEST"
    HOTEL_MANAGER = "HOTEL_MANAGER"
    ADMIN = "ADMIN"

    CHOICES = [
        (GUEST, "Guest"),
        (HOTEL_MANAGER, "Hotel Manager"),
        (ADMIN, "Admin"),
    ]

    ALL_ROLES = [GUEST, HOTEL_MANAGER, ADMIN]


class UserManager(BaseUserManager):
    """
    Custom user manager that uses email as the unique identifier
    instead of username.
    """

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError("The email field is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("roles", [UserRole.GUEST])
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with all roles and admin privileges."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("roles", [UserRole.ADMIN, UserRole.HOTEL_MANAGER, UserRole.GUEST])

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model that uses email as the login identifier.

    Fields (matching ER schema):
        - id: BigAutoField (PK)
        - name: Full name
        - email: Unique email (used for login)
        - password: Hashed password
        - roles: List of roles (GUEST, HOTEL_MANAGER, ADMIN)
    """

    # Remove the default username field
    username = None

    # Core fields matching the ER schema
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    roles = models.JSONField(
        default=list,
        help_text="List of user roles: GUEST, HOTEL_MANAGER, ADMIN",
    )

    # Use email as the login identifier
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.name} ({self.email})"

    # ─── Role Helpers ───────────────────────────────────────────────────────

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in (self.roles or [])

    @property
    def is_guest(self) -> bool:
        return self.has_role(UserRole.GUEST)

    @property
    def is_hotel_manager(self) -> bool:
        return self.has_role(UserRole.HOTEL_MANAGER)

    @property
    def is_admin_user(self) -> bool:
        return self.has_role(UserRole.ADMIN)

    def add_role(self, role: str):
        """Add a role to the user if not already present."""
        if role not in (self.roles or []):
            self.roles = (self.roles or []) + [role]
            self.save(update_fields=["roles"])

    def remove_role(self, role: str):
        """Remove a role from the user."""
        if role in (self.roles or []):
            self.roles = [r for r in self.roles if r != role]
            self.save(update_fields=["roles"])
