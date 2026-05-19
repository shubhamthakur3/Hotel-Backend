"""
Tests for authentication endpoints: signup, login, token refresh.
"""

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole


class TestSignup(TestCase):
    """Test user registration endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/signup"

    def test_signup_success(self):
        """Test successful user registration."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access_token", response.data)
        self.assertEqual(response.data["user"]["email"], "john@example.com")
        self.assertEqual(response.data["user"]["roles"], [UserRole.GUEST])

        # Verify user was created in DB
        user = User.objects.get(email="john@example.com")
        self.assertEqual(user.name, "John Doe")
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_signup_duplicate_email(self):
        """Test registration with existing email fails."""
        User.objects.create_user(
            email="existing@example.com",
            password="Password123!",
            name="Existing User",
        )

        data = {
            "name": "New User",
            "email": "existing@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_password_mismatch(self):
        """Test registration with mismatched passwords fails."""
        data = {
            "name": "John",
            "email": "john@example.com",
            "password": "StrongPass123!",
            "confirm_password": "DifferentPass!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_weak_password(self):
        """Test registration with weak password fails."""
        data = {
            "name": "John",
            "email": "john@example.com",
            "password": "123",
            "confirm_password": "123",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_sets_refresh_cookie(self):
        """Test that signup sets an HttpOnly refresh token cookie."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("refresh_token", response.cookies)


class TestLogin(TestCase):
    """Test user login endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/login"
        self.user = User.objects.create_user(
            email="john@example.com",
            password="StrongPass123!",
            name="John Doe",
        )

    def test_login_success(self):
        """Test successful login."""
        data = {
            "email": "john@example.com",
            "password": "StrongPass123!",
        }
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertEqual(response.data["user"]["email"], "john@example.com")

    def test_login_wrong_password(self):
        """Test login with wrong password fails."""
        data = {
            "email": "john@example.com",
            "password": "WrongPassword!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user(self):
        """Test login with non-existent email fails."""
        data = {
            "email": "nonexistent@example.com",
            "password": "SomePass123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_sets_refresh_cookie(self):
        """Test that login sets an HttpOnly refresh token cookie."""
        data = {
            "email": "john@example.com",
            "password": "StrongPass123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh_token", response.cookies)


class TestTokenRefresh(TestCase):
    """Test token refresh endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="john@example.com",
            password="StrongPass123!",
            name="John Doe",
        )

    def test_refresh_without_cookie(self):
        """Test refresh without refresh token cookie fails."""
        response = self.client.post("/api/auth/refresh", format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestRolePermissions(TestCase):
    """Test role-based access control."""

    def setUp(self):
        self.client = APIClient()
        self.guest = User.objects.create_user(
            email="guest@example.com",
            password="Pass123!",
            name="Guest User",
            roles=[UserRole.GUEST],
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="Pass123!",
            name="Manager User",
            roles=[UserRole.HOTEL_MANAGER],
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="Pass123!",
            name="Admin User",
            roles=[UserRole.ADMIN],
        )

    def test_guest_role_check(self):
        """Test guest role properties."""
        self.assertTrue(self.guest.is_guest)
        self.assertFalse(self.guest.is_hotel_manager)
        self.assertFalse(self.guest.is_admin_user)

    def test_manager_role_check(self):
        """Test manager role properties."""
        self.assertTrue(self.manager.is_hotel_manager)
        self.assertFalse(self.manager.is_guest)

    def test_admin_role_check(self):
        """Test admin role properties."""
        self.assertTrue(self.admin.is_admin_user)

    def test_add_role(self):
        """Test adding a role to a user."""
        self.guest.add_role(UserRole.HOTEL_MANAGER)
        self.assertTrue(self.guest.is_hotel_manager)
        self.assertTrue(self.guest.is_guest)

    def test_remove_role(self):
        """Test removing a role from a user."""
        self.manager.remove_role(UserRole.HOTEL_MANAGER)
        self.assertFalse(self.manager.is_hotel_manager)

    def test_guest_cannot_access_admin_hotels(self):
        """Test that a guest cannot access admin hotel endpoints."""
        self.client.force_authenticate(user=self.guest)
        response = self.client.get("/api/admin/hotels/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_access_admin_hotels(self):
        """Test that a manager can access admin hotel endpoints."""
        self.client.force_authenticate(user=self.manager)
        response = self.client.get("/api/admin/hotels/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
