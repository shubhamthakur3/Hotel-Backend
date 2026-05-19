"""
Inventory service layer — the heart of the booking system.

Handles:
- Initializing 365 days of inventory for a room
- Pessimistic locking for concurrency-safe booking
- Reserving and releasing inventory
"""

import logging
from datetime import date, timedelta
from typing import List

from django.conf import settings
from django.db import transaction
from django.db.models import F

from apps.common.exceptions import InventoryException, ResourceNotFoundException
from apps.common.utils import generate_date_range

from .models import Inventory

logger = logging.getLogger(__name__)


class InventoryService:
    """Core inventory management with concurrency-safe operations."""

    @staticmethod
    def initialize_room_for_a_year(room) -> int:
        """
        Create 365 days of Inventory records for a room.

        Called when:
        - A new room is created under an active hotel
        - A hotel is activated

        Returns the number of records created.
        """
        today = date.today()
        days = settings.INVENTORY_INIT_DAYS  # 365

        # Build inventory records in bulk
        inventory_records = []
        for i in range(days):
            inv_date = today + timedelta(days=i)
            inventory_records.append(
                Inventory(
                    hotel=room.hotel,
                    room=room,
                    date=inv_date,
                    total_count=room.total_count,
                    booked_count=0,
                    surge_factor=1.00,
                    closed=False,
                )
            )

        # Use ignore_conflicts to handle re-initialization safely
        created = Inventory.objects.bulk_create(
            inventory_records,
            ignore_conflicts=True,
            batch_size=500,
        )

        logger.info(
            "Initialized %d inventory records for room %s (id=%d)",
            len(created), room.get_type_display(), room.id,
        )
        return len(created)

    @staticmethod
    def find_and_lock_available_inventory(
        room_id: int,
        check_in: date,
        check_out: date,
    ) -> List[Inventory]:
        """
        Find and pessimistic-lock inventory rows for the given date range.

        MUST be called inside transaction.atomic().
        Uses select_for_update() to prevent double bookings.

        Args:
            room_id: The room type to book
            check_in: Check-in date (inclusive)
            check_out: Check-out date (exclusive)

        Returns:
            List of locked Inventory rows

        Raises:
            InventoryException: If any date is unavailable or closed
        """
        stay_dates = generate_date_range(check_in, check_out)
        if not stay_dates:
            raise InventoryException("Invalid date range.")

        # Lock the rows — this blocks other transactions from modifying them
        inventory_rows = list(
            Inventory.objects.select_for_update()
            .filter(
                room_id=room_id,
                date__in=stay_dates,
            )
            .order_by("date")
        )

        # Verify we have inventory for ALL dates
        if len(inventory_rows) != len(stay_dates):
            found_dates = {row.date for row in inventory_rows}
            missing = [d for d in stay_dates if d not in found_dates]
            raise InventoryException(
                f"Inventory not available for dates: {[str(d) for d in missing]}"
            )

        # Verify availability for each date
        for row in inventory_rows:
            if row.closed:
                raise InventoryException(
                    f"Date {row.date} is closed for bookings."
                )
            if row.booked_count >= row.total_count:
                raise InventoryException(
                    f"No availability on {row.date}. All {row.total_count} rooms are booked."
                )

        return inventory_rows

    @staticmethod
    def reserve_inventory(inventory_rows: List[Inventory]) -> None:
        """
        Reserve one unit on each inventory row by incrementing booked_count.

        Uses F() expressions for atomic increment to avoid race conditions
        even with optimistic concurrency.
        """
        for row in inventory_rows:
            Inventory.objects.filter(id=row.id).update(
                booked_count=F("booked_count") + 1,
            )

        logger.info(
            "Reserved inventory for %d dates (room_id=%d)",
            len(inventory_rows),
            inventory_rows[0].room_id if inventory_rows else 0,
        )

    @staticmethod
    def release_inventory(room_id: int, check_in: date, check_out: date) -> None:
        """
        Release a reservation by decrementing booked_count.

        Called on booking cancellation or expiration.
        Uses F() expression to prevent going below 0.
        """
        stay_dates = generate_date_range(check_in, check_out)

        with transaction.atomic():
            updated = Inventory.objects.filter(
                room_id=room_id,
                date__in=stay_dates,
                booked_count__gt=0,
            ).update(
                booked_count=F("booked_count") - 1,
            )

        logger.info(
            "Released inventory for %d dates (room_id=%d)",
            updated, room_id,
        )

    @staticmethod
    def get_room_inventory(room_id: int, start_date: date = None, end_date: date = None):
        """
        Get inventory records for a room, optionally filtered by date range.
        """
        queryset = Inventory.objects.filter(room_id=room_id)

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset.order_by("date")

    @staticmethod
    def update_inventory_bulk(room_id: int, updates: list) -> int:
        """
        Bulk update inventory records for a room.

        Each update is a dict with 'date' and optional fields:
        'surge_factor', 'closed', 'total_count'.
        """
        updated_count = 0
        for update in updates:
            inv_date = update.pop("date")
            if update:
                count = Inventory.objects.filter(
                    room_id=room_id,
                    date=inv_date,
                ).update(**update)
                updated_count += count

        logger.info(
            "Bulk updated %d inventory records for room_id=%d",
            updated_count, room_id,
        )
        return updated_count
