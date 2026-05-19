"""Celery tasks for booking management."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.bookings.tasks.expire_stale_reservations")
def expire_stale_reservations():
    """
    Expire unpaid reservations that have exceeded the timeout.
    Runs every 5 minutes via Celery Beat.
    """
    from .services import BookingService

    expired_count = BookingService.expire_stale_reservations()
    logger.info("Expired %d stale reservations.", expired_count)
    return expired_count
