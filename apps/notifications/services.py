"""
Notification service — convenience wrappers for triggering notifications.
"""

import logging

from django.db import transaction

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for triggering notifications after booking events."""

    @staticmethod
    def notify_booking_confirmed(booking_id: int):
        """Schedule confirmation email after transaction commits."""
        from .tasks import send_booking_confirmation_email
        transaction.on_commit(
            lambda: send_booking_confirmation_email.delay(booking_id)
        )

    @staticmethod
    def notify_booking_cancelled(booking_id: int):
        """Schedule cancellation email after transaction commits."""
        from .tasks import send_booking_cancellation_email
        transaction.on_commit(
            lambda: send_booking_cancellation_email.delay(booking_id)
        )
