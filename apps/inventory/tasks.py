"""Celery tasks for inventory management."""

import logging
from datetime import date

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.inventory.tasks.cleanup_expired_inventory")
def cleanup_expired_inventory():
    """
    Remove inventory records older than today.
    Runs daily at 00:30 via Celery Beat.
    """
    from .models import Inventory

    today = date.today()
    deleted_count, _ = Inventory.objects.filter(date__lt=today).delete()
    logger.info("Cleaned up %d expired inventory records.", deleted_count)
    return deleted_count
