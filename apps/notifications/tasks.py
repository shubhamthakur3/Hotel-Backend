"""
Notification Celery tasks — sends emails for booking lifecycle events.

All email sending is done asynchronously via Celery to keep
API response times fast.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.notifications.tasks.send_booking_confirmation_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_booking_confirmation_email(self, booking_id: int):
    """
    Send booking confirmation email to the customer.

    Triggered via transaction.on_commit() after payment confirmation.
    """
    try:
        from apps.bookings.models import Booking
        booking = Booking.objects.select_related("hotel", "room", "user").get(id=booking_id)

        subject = f"Booking Confirmed - {booking.hotel.name} (#{booking.id})"
        message = (
            f"Dear {booking.user.name},\n\n"
            f"Your booking has been confirmed!\n\n"
            f"Booking Details:\n"
            f"  Hotel: {booking.hotel.name}\n"
            f"  Room: {booking.room.get_type_display()}\n"
            f"  Check-in: {booking.check_in_date}\n"
            f"  Check-out: {booking.checkout_date}\n"
            f"  Total Price: ${booking.total_price}\n"
            f"  Booking ID: #{booking.id}\n\n"
            f"Thank you for choosing our platform!\n"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.user.email],
            fail_silently=False,
        )

        logger.info("Confirmation email sent for booking #%d to %s", booking_id, booking.user.email)

    except Exception as exc:
        logger.error("Failed to send confirmation email for booking #%d: %s", booking_id, str(exc))
        raise self.retry(exc=exc)


@shared_task(
    name="apps.notifications.tasks.send_booking_cancellation_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_booking_cancellation_email(self, booking_id: int):
    """Send booking cancellation email to the customer."""
    try:
        from apps.bookings.models import Booking
        booking = Booking.objects.select_related("hotel", "user").get(id=booking_id)

        subject = f"Booking Cancelled - {booking.hotel.name} (#{booking.id})"
        message = (
            f"Dear {booking.user.name},\n\n"
            f"Your booking #{booking.id} at {booking.hotel.name} has been cancelled.\n\n"
            f"If you did not request this cancellation, please contact our support team.\n"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.user.email],
            fail_silently=False,
        )

        logger.info("Cancellation email sent for booking #%d", booking_id)

    except Exception as exc:
        logger.error("Failed to send cancellation email for booking #%d: %s", booking_id, str(exc))
        raise self.retry(exc=exc)


@shared_task(name="apps.notifications.tasks.send_payment_receipt_email")
def send_payment_receipt_email(booking_id: int):
    """Send payment receipt email."""
    try:
        from apps.bookings.models import Booking
        booking = Booking.objects.select_related("hotel", "user", "payment").get(id=booking_id)

        if not booking.payment:
            return

        subject = f"Payment Receipt - Booking #{booking.id}"
        message = (
            f"Dear {booking.user.name},\n\n"
            f"Payment received for booking #{booking.id}.\n\n"
            f"Amount: ${booking.payment.price}\n"
            f"Transaction ID: {booking.payment.transaction_id}\n"
            f"Hotel: {booking.hotel.name}\n\n"
            f"Thank you!\n"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.user.email],
            fail_silently=False,
        )

        logger.info("Payment receipt email sent for booking #%d", booking_id)

    except Exception as exc:
        logger.error("Failed to send payment receipt for booking #%d: %s", booking_id, str(exc))
