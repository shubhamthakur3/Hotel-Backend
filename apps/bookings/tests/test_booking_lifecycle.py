"""
Tests for booking lifecycle: init, add guests, cancel, confirm.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.bookings.models import Booking, BookingStatus
from apps.hotels.models import Hotel
from apps.inventory.services import InventoryService
from apps.rooms.models import Room
from apps.users.models import Guest


class TestBookingLifecycle(TestCase):
    """Test the complete booking lifecycle."""

    def setUp(self):
        self.client = APIClient()

        # Create manager and hotel
        self.manager = User.objects.create_user(
            email="manager@hotel.com",
            password="ManagerPass123!",
            name="Hotel Manager",
            roles=[UserRole.HOTEL_MANAGER],
        )

        self.hotel = Hotel.objects.create(
            name="Test Hotel",
            city="New York",
            active=True,
            owner=self.manager,
        )

        self.room = Room.objects.create(
            hotel=self.hotel,
            type="DELUXE",
            base_price=Decimal("150.00"),
            total_count=5,
            capacity=2,
        )

        # Initialize inventory
        InventoryService.initialize_room_for_a_year(self.room)

        # Create guest user
        self.user = User.objects.create_user(
            email="guest@example.com",
            password="GuestPass123!",
            name="Guest User",
            roles=[UserRole.GUEST],
        )

        # Create guest profile
        self.guest = Guest.objects.create(
            user=self.user,
            name="John Traveler",
            gender="MALE",
        )

        self.client.force_authenticate(user=self.user)

    def test_initialize_booking_success(self):
        """Test successful booking initialization."""
        check_in = date.today() + timedelta(days=10)
        check_out = date.today() + timedelta(days=13)

        response = self.client.post(
            "/api/bookings/init",
            {
                "room_id": self.room.id,
                "check_in_date": check_in.isoformat(),
                "checkout_date": check_out.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["booking"]["id"])
        self.assertEqual(booking.status, BookingStatus.RESERVED)
        self.assertEqual(booking.user, self.user)
        self.assertGreater(booking.total_price, 0)

    def test_initialize_booking_past_date(self):
        """Test booking with past check-in date fails."""
        response = self.client.post(
            "/api/bookings/init",
            {
                "room_id": self.room.id,
                "check_in_date": (date.today() - timedelta(days=1)).isoformat(),
                "checkout_date": date.today().isoformat(),
            },
            format="json",
        )

        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT])

    def test_initialize_booking_invalid_dates(self):
        """Test booking with check_out before check_in fails."""
        check_in = date.today() + timedelta(days=10)
        check_out = date.today() + timedelta(days=5)

        response = self.client.post(
            "/api/bookings/init",
            {
                "room_id": self.room.id,
                "check_in_date": check_in.isoformat(),
                "checkout_date": check_out.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_guests_to_booking(self):
        """Test adding guests to a reservation."""
        # Create booking
        check_in = date.today() + timedelta(days=10)
        check_out = date.today() + timedelta(days=12)

        response = self.client.post(
            "/api/bookings/init",
            {
                "room_id": self.room.id,
                "check_in_date": check_in.isoformat(),
                "checkout_date": check_out.isoformat(),
            },
            format="json",
        )
        booking_id = response.data["booking"]["id"]

        # Add guests
        response = self.client.post(
            f"/api/bookings/{booking_id}/addGuests",
            {"guest_ids": [self.guest.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking = Booking.objects.get(id=booking_id)
        self.assertEqual(booking.status, BookingStatus.GUESTS_ADDED)

    def test_cancel_booking(self):
        """Test booking cancellation releases inventory."""
        from apps.inventory.models import Inventory

        check_in = date.today() + timedelta(days=20)
        check_out = date.today() + timedelta(days=22)

        # Check initial inventory
        inv_before = Inventory.objects.get(room=self.room, date=check_in)
        initial_booked = inv_before.booked_count

        # Create booking
        response = self.client.post(
            "/api/bookings/init",
            {
                "room_id": self.room.id,
                "check_in_date": check_in.isoformat(),
                "checkout_date": check_out.isoformat(),
            },
            format="json",
        )
        booking_id = response.data["booking"]["id"]

        # Verify inventory was reserved
        inv_after_reserve = Inventory.objects.get(room=self.room, date=check_in)
        self.assertEqual(inv_after_reserve.booked_count, initial_booked + 1)

        # Cancel
        response = self.client.post(f"/api/bookings/{booking_id}/cancel")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify inventory was released
        inv_after_cancel = Inventory.objects.get(room=self.room, date=check_in)
        self.assertEqual(inv_after_cancel.booked_count, initial_booked)

        booking = Booking.objects.get(id=booking_id)
        self.assertEqual(booking.status, BookingStatus.CANCELLED)

    def test_booking_status_check(self):
        """Test checking booking status."""
        check_in = date.today() + timedelta(days=10)
        check_out = date.today() + timedelta(days=12)

        response = self.client.post(
            "/api/bookings/init",
            {
                "room_id": self.room.id,
                "check_in_date": check_in.isoformat(),
                "checkout_date": check_out.isoformat(),
            },
            format="json",
        )
        booking_id = response.data["booking"]["id"]

        response = self.client.get(f"/api/bookings/{booking_id}/status")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], BookingStatus.RESERVED)
