"""Celery tasks for pricing updates."""

import logging
from datetime import date, timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.pricing.tasks.update_hotel_min_prices")
def update_hotel_min_prices():
    """
    Recalculate HotelMinPrice for all active hotels.

    Runs hourly via Celery Beat. For each hotel, finds the minimum
    room price for each date over the next 30 days and stores it
    in the HotelMinPrice table for fast search queries.
    """
    from apps.hotels.models import Hotel, HotelMinPrice
    from apps.inventory.models import Inventory
    from apps.pricing.services import PricingService

    today = date.today()
    end_date = today + timedelta(days=30)  # Only update next 30 days per run

    hotels = Hotel.objects.filter(active=True).prefetch_related("rooms")
    total_updated = 0

    for hotel in hotels:
        rooms = hotel.rooms.all()
        if not rooms:
            continue

        for day_offset in range(30):
            target_date = today + timedelta(days=day_offset)
            min_price = None

            for room in rooms:
                # Get inventory for this room on this date
                try:
                    inv = Inventory.objects.get(room=room, date=target_date)
                    if inv.closed or inv.available_count <= 0:
                        continue
                except Inventory.DoesNotExist:
                    continue

                price = PricingService.calculate_dynamic_price(room, target_date, inv)
                if min_price is None or price < min_price:
                    min_price = price

            if min_price is not None:
                HotelMinPrice.objects.update_or_create(
                    hotel=hotel,
                    date=target_date,
                    defaults={"min_price": min_price},
                )
                total_updated += 1

    logger.info("Updated %d HotelMinPrice records.", total_updated)
    return total_updated
