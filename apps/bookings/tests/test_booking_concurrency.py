"""
Tests for concurrency / double-booking prevention.

Uses threads to simulate simultaneous booking attempts and
verifies that select_for_update() prevents overselling.
"""

import threading
from datetime import date, timedelta
from decimal import Decimal

from django.test import TransactionTestCase

from apps.accounts.models import User, UserRole
from apps.bookings.models import Booking, BookingStatus
from apps.bookings.services import BookingService
from apps.hotels.models import Hotel
from apps.inventory.models import Inventory
from apps.inventory.services import InventoryService
from apps.rooms.models import Room


class TestBookingConcurrency(TransactionTestCase):
    """
    Test concurrent booking attempts to verify double-booking prevention.

    Uses TransactionTestCase (not TestCase) because select_for_update()
    requires actual database transactions to work correctly.
    """

    def setUp(self):
        # Create hotel with a room that has only 1 unit
        self.manager = User.objects.create_user(
            email="manager@test.com",
            password="Pass123!",
            name="Manager",
            roles=[UserRole.HOTEL_MANAGER],
        )

        self.hotel = Hotel.objects.create(
            name="Concurrency Test Hotel",
            city="Test City",
            active=True,
            owner=self.manager,
        )

        # Room with only 1 unit — only one booking should succeed
        self.room = Room.objects.create(
            hotel=self.hotel,
            type="SUITE",
            base_price=Decimal("200.00"),
            total_count=1,
            capacity=2,
        )

        InventoryService.initialize_room_for_a_year(self.room)

        # Create two users who will try to book simultaneously
        self.user1 = User.objects.create_user(
            email="user1@test.com",
            password="Pass123!",
            name="User 1",
            roles=[UserRole.GUEST],
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com",
            password="Pass123!",
            name="User 2",
            roles=[UserRole.GUEST],
        )

    def test_concurrent_booking_only_one_succeeds(self):
        """
        Two users book the same room on the same dates simultaneously.
        Only one should succeed; the other should fail.
        """
        check_in = date.today() + timedelta(days=30)
        check_out = date.today() + timedelta(days=32)

        results = {"user1": None, "user2": None}
        errors = {"user1": None, "user2": None}

        def book_as_user(user, result_key):
            try:
                booking = BookingService.initialize_booking(
                    user=user,
                    room_id=self.room.id,
                    check_in=check_in,
                    check_out=check_out,
                )
                results[result_key] = booking
            except Exception as e:
                errors[result_key] = str(e)

        # Launch two threads simultaneously
        t1 = threading.Thread(target=book_as_user, args=(self.user1, "user1"))
        t2 = threading.Thread(target=book_as_user, args=(self.user2, "user2"))

        t1.start()
        t2.start()

        t1.join(timeout=10)
        t2.join(timeout=10)

        # Count successes
        successes = sum(1 for r in results.values() if r is not None)
        failures = sum(1 for e in errors.values() if e is not None)

        # Exactly one should succeed
        self.assertEqual(successes, 1, f"Expected 1 success, got {successes}. Results: {results}, Errors: {errors}")
        self.assertEqual(failures, 1, f"Expected 1 failure, got {failures}")

        # Verify inventory is correctly booked
        inv = Inventory.objects.get(room=self.room, date=check_in)
        self.assertEqual(inv.booked_count, 1)
        self.assertEqual(inv.available_count, 0)

    def test_sequential_bookings_exhaust_inventory(self):
        """
        Book all available units one by one.
        The last booking attempt should fail.
        """
        check_in = date.today() + timedelta(days=40)
        check_out = date.today() + timedelta(days=42)

        # Room has total_count=1, so first booking should succeed
        booking = BookingService.initialize_booking(
            user=self.user1,
            room_id=self.room.id,
            check_in=check_in,
            check_out=check_out,
        )
        self.assertEqual(booking.status, BookingStatus.RESERVED)

        # Second booking should fail (no availability)
        with self.assertRaises(Exception):
            BookingService.initialize_booking(
                user=self.user2,
                room_id=self.room.id,
                check_in=check_in,
                check_out=check_out,
            )

    def test_cancel_then_rebook(self):
        """
        After cancellation, inventory should be available again.
        """
        check_in = date.today() + timedelta(days=50)
        check_out = date.today() + timedelta(days=52)

        # Book
        booking = BookingService.initialize_booking(
            user=self.user1,
            room_id=self.room.id,
            check_in=check_in,
            check_out=check_out,
        )

        # Cancel
        BookingService.cancel_booking(booking.id, self.user1)

        # Verify inventory is released
        inv = Inventory.objects.get(room=self.room, date=check_in)
        self.assertEqual(inv.booked_count, 0)

        # Rebook should succeed
        new_booking = BookingService.initialize_booking(
            user=self.user2,
            room_id=self.room.id,
            check_in=check_in,
            check_out=check_out,
        )
        self.assertEqual(new_booking.status, BookingStatus.RESERVED)
