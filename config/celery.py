"""
Celery application configuration for Hotel Backend API.

Auto-discovers tasks from all installed Django apps.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("hotel_backend")

# Load config from Django settings, using the CELERY_ namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# ─── Periodic Task Schedule (Celery Beat) ───────────────────────────────────────

app.conf.beat_schedule = {
    "expire-stale-reservations": {
        "task": "apps.bookings.tasks.expire_stale_reservations",
        "schedule": 300.0,  # Every 5 minutes
    },
    "update-hotel-min-prices": {
        "task": "apps.pricing.tasks.update_hotel_min_prices",
        "schedule": crontab(minute=0),  # Every hour
    },
    "cleanup-expired-inventory": {
        "task": "apps.inventory.tasks.cleanup_expired_inventory",
        "schedule": crontab(hour=0, minute=30),  # Daily at 00:30
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for verifying Celery is working."""
    print(f"Request: {self.request!r}")
