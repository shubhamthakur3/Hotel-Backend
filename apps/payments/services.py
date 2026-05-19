"""
Stripe checkout and payment processing service.

Handles:
- Creating Stripe Checkout Sessions
- Processing webhook events
- Idempotent payment confirmation
"""

import logging

import stripe
from django.conf import settings
from django.db import transaction

from apps.bookings.models import BookingStatus
from apps.common.exceptions import BookingException, PaymentException

from .models import Payment, PaymentStatus

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class CheckoutService:
    """Handles Stripe Checkout Session creation."""

    @staticmethod
    def create_checkout_session(booking) -> dict:
        """
        Create a Stripe Checkout Session for a booking.

        Args:
            booking: Booking instance

        Returns:
            dict with session_url and session_id

        Raises:
            BookingException: If booking is in wrong state
            PaymentException: If Stripe API call fails
        """
        # Validate booking state
        if booking.status not in (BookingStatus.RESERVED, BookingStatus.GUESTS_ADDED):
            raise BookingException(
                f"Cannot initiate payment for a booking in '{booking.status}' status. "
                f"Booking must be in RESERVED or GUESTS_ADDED state."
            )

        try:
            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"Hotel Booking #{booking.id}",
                                "description": (
                                    f"{booking.room.get_type_display()} at {booking.hotel.name} | "
                                    f"{booking.check_in_date} to {booking.checkout_date}"
                                ),
                            },
                            "unit_amount": int(booking.total_price * 100),  # Stripe uses cents
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=f"{settings.FRONTEND_URL}/bookings/{booking.id}/success",
                cancel_url=f"{settings.FRONTEND_URL}/bookings/{booking.id}/cancel",
                metadata={
                    "booking_id": str(booking.id),
                    "hotel_id": str(booking.hotel_id),
                    "user_id": str(booking.user_id),
                },
                expires_after=1800,  # 30 minutes
            )

            # Create Payment record
            payment = Payment.objects.create(
                transaction_id=session.id,
                price=booking.total_price,
                status=PaymentStatus.PENDING,
            )

            # Update booking status
            booking.payment = payment
            booking.status = BookingStatus.PAYMENTS_PENDING
            booking.save(update_fields=["payment", "status", "updated_at"])

            logger.info(
                "Stripe checkout session created: %s for booking #%d",
                session.id, booking.id,
            )

            return {
                "session_url": session.url,
                "session_id": session.id,
            }

        except stripe.error.StripeError as e:
            logger.error("Stripe error creating checkout session: %s", str(e))
            raise PaymentException(f"Payment processing failed: {str(e)}")


class WebhookService:
    """Handles Stripe webhook event processing."""

    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
        """
        Verify Stripe webhook signature and return the event.

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header value

        Returns:
            Stripe event object

        Raises:
            PaymentException: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET,
            )
            return event
        except ValueError:
            raise PaymentException("Invalid webhook payload.")
        except stripe.error.SignatureVerificationError:
            raise PaymentException("Invalid webhook signature.")

    @staticmethod
    def handle_checkout_completed(session: dict) -> None:
        """
        Handle the checkout.session.completed event.

        This is the source of truth for payment confirmation.
        Implements idempotency — safe to call multiple times.
        """
        session_id = session.get("id")
        booking_id = session.get("metadata", {}).get("booking_id")

        if not session_id or not booking_id:
            logger.warning("Webhook missing session_id or booking_id metadata.")
            return

        try:
            payment = Payment.objects.get(transaction_id=session_id)
        except Payment.DoesNotExist:
            logger.error("Payment not found for session: %s", session_id)
            return

        # Idempotency check — skip if already confirmed
        if payment.status == PaymentStatus.CONFIRMED:
            logger.info(
                "Payment %s already confirmed (idempotent skip).",
                session_id,
            )
            return

        # Confirm the payment
        with transaction.atomic():
            payment.status = PaymentStatus.CONFIRMED
            payment.save(update_fields=["status", "updated_at"])

            # Confirm the booking
            from apps.bookings.services import BookingService
            BookingService.confirm_booking(int(booking_id), payment)

        logger.info(
            "Payment confirmed: %s → Booking #%s CONFIRMED.",
            session_id, booking_id,
        )

    @staticmethod
    def handle_checkout_expired(session: dict) -> None:
        """Handle the checkout.session.expired event."""
        session_id = session.get("id")
        booking_id = session.get("metadata", {}).get("booking_id")

        if not session_id or not booking_id:
            return

        try:
            payment = Payment.objects.get(transaction_id=session_id)
            if payment.status != PaymentStatus.PENDING:
                return  # Already processed

            payment.status = PaymentStatus.FAILED
            payment.save(update_fields=["status", "updated_at"])

            from apps.bookings.services import BookingService
            BookingService.mark_booking_failed(int(booking_id))

            logger.info(
                "Checkout expired: %s → Booking #%s FAILED.",
                session_id, booking_id,
            )
        except Payment.DoesNotExist:
            logger.warning("Payment not found for expired session: %s", session_id)

    @staticmethod
    def handle_payment_failed(session: dict) -> None:
        """Handle payment intent failed events."""
        WebhookService.handle_checkout_expired(session)
