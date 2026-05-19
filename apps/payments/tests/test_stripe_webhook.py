"""
Tests for Stripe webhook handling and payment processing.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.bookings.models import Booking, BookingStatus
from apps.hotels.models import Hotel
from apps.inventory.services import InventoryService
from apps.payments.models import Payment, PaymentStatus
from apps.payments.services import WebhookService
from apps.rooms.models import Room


class TestWebhookService(TestCase):
    """Test Stripe webhook processing logic."""

    def setUp(self):
        self.manager = User.objects.create_user(
            email="manager@test.com", password="Pass123!", name="Manager",
            roles=[UserRole.HOTEL_MANAGER],
        )
        self.user = User.objects.create_user(
            email="user@test.com", password="Pass123!", name="User",
            roles=[UserRole.GUEST],
        )
        self.hotel = Hotel.objects.create(
            name="Test Hotel", city="NYC", active=True, owner=self.manager,
        )
        self.room = Room.objects.create(
            hotel=self.hotel, type="STANDARD", base_price=Decimal("100.00"),
            total_count=5, capacity=2,
        )
        InventoryService.initialize_room_for_a_year(self.room)

        check_in = date.today() + timedelta(days=10)
        check_out = date.today() + timedelta(days=12)

        # Create payment
        self.payment = Payment.objects.create(
            transaction_id="cs_test_session_123",
            price=Decimal("200.00"),
            status=PaymentStatus.PENDING,
        )

        # Create booking in PAYMENTS_PENDING state
        self.booking = Booking.objects.create(
            hotel=self.hotel, room=self.room, user=self.user,
            check_in_date=check_in, checkout_date=check_out,
            status=BookingStatus.PAYMENTS_PENDING,
            total_price=Decimal("200.00"),
            payment=self.payment,
        )

    @patch("apps.notifications.tasks.send_booking_confirmation_email.delay")
    def test_checkout_completed_confirms_booking(self, mock_email):
        """Test that checkout.session.completed confirms the booking."""
        session = {
            "id": "cs_test_session_123",
            "metadata": {"booking_id": str(self.booking.id)},
        }

        WebhookService.handle_checkout_completed(session)

        # Verify payment confirmed
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.CONFIRMED)

        # Verify booking confirmed
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, BookingStatus.CONFIRMED)

    @patch("apps.notifications.tasks.send_booking_confirmation_email.delay")
    def test_checkout_completed_idempotent(self, mock_email):
        """Test that duplicate webhook calls are handled idempotently."""
        session = {
            "id": "cs_test_session_123",
            "metadata": {"booking_id": str(self.booking.id)},
        }

        # Call twice
        WebhookService.handle_checkout_completed(session)
        WebhookService.handle_checkout_completed(session)

        # Should still be confirmed (not error)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.CONFIRMED)

    def test_checkout_expired_fails_booking(self):
        """Test that checkout.session.expired marks booking as failed."""
        # Reset to PENDING for this test
        self.payment.status = PaymentStatus.PENDING
        self.payment.save()

        session = {
            "id": "cs_test_session_123",
            "metadata": {"booking_id": str(self.booking.id)},
        }

        WebhookService.handle_checkout_expired(session)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.FAILED)


class TestStripeWebhookEndpoint(TestCase):
    """Test the webhook endpoint itself."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/webhook/payment"

    @patch("apps.payments.services.stripe.Webhook.construct_event")
    def test_valid_webhook(self, mock_construct):
        """Test that a valid webhook is processed."""
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test", "metadata": {}}},
        }

        response = self.client.post(
            self.url, data=b'{}', content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )
        self.assertEqual(response.status_code, 200)

    def test_missing_signature_rejected(self):
        """Test that requests without Stripe signature are rejected."""
        with patch("apps.payments.services.stripe.Webhook.construct_event") as mock:
            mock.side_effect = Exception("Invalid signature")
            response = self.client.post(
                self.url, data=b'{}', content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
