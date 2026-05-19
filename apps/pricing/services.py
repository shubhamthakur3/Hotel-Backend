"""
Dynamic pricing service.

Composes multiple pricing strategies to calculate the final
nightly price for a room on a specific date.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import List

from apps.common.utils import round_price

from .strategies import (
    HolidayPricingStrategy,
    OccupancyPricingStrategy,
    PricingContext,
    PricingStrategy,
    SurgePricingStrategy,
    UrgencyPricingStrategy,
    WeekendPricingStrategy,
)

logger = logging.getLogger(__name__)

# Default strategy chain — order matters
DEFAULT_STRATEGIES: List[PricingStrategy] = [
    SurgePricingStrategy(),
    WeekendPricingStrategy(),
    HolidayPricingStrategy(),
    OccupancyPricingStrategy(),
    UrgencyPricingStrategy(),
]


class PricingService:
    """
    Composes pricing strategies to calculate dynamic room prices.

    Usage:
        price = PricingService.calculate_dynamic_price(room, date, inventory_row)
    """

    @staticmethod
    def calculate_dynamic_price(
        room,
        target_date: date,
        inventory_row=None,
        strategies: List[PricingStrategy] = None,
    ) -> Decimal:
        """
        Calculate the dynamic price for a room on a specific date.

        Applies all strategies sequentially:
            Base Price × Strategy1 × Strategy2 × ... = Final Price

        Args:
            room: Room instance
            target_date: The date to price
            inventory_row: Optional Inventory record for this date
            strategies: Optional custom strategy list

        Returns:
            Decimal: Final calculated price, rounded to 2 decimal places
        """
        if strategies is None:
            strategies = DEFAULT_STRATEGIES

        # Build pricing context
        context = PricingContext(
            room_base_price=room.base_price,
            date=target_date,
            surge_factor=Decimal(str(inventory_row.surge_factor)) if inventory_row else Decimal("1.00"),
            booked_count=inventory_row.booked_count if inventory_row else 0,
            total_count=inventory_row.total_count if inventory_row else room.total_count,
            today=date.today(),
        )

        # Apply each strategy
        price = room.base_price
        for strategy in strategies:
            multiplier = strategy.calculate_multiplier(context)
            price *= multiplier
            logger.debug(
                "Strategy %s: multiplier=%.2f, price=%.2f",
                strategy.name, multiplier, price,
            )

        final_price = round_price(price)
        logger.debug(
            "Final price for %s on %s: $%.2f (base: $%.2f)",
            room, target_date, final_price, room.base_price,
        )
        return final_price

    @staticmethod
    def calculate_total_stay_price(
        room,
        check_in: date,
        check_out: date,
        inventory_rows: list = None,
    ) -> Decimal:
        """
        Calculate the total price for a multi-night stay.

        Args:
            room: Room instance
            check_in: Check-in date
            check_out: Check-out date
            inventory_rows: Optional list of Inventory records

        Returns:
            Decimal: Total price for the entire stay
        """
        from apps.common.utils import generate_date_range

        stay_dates = generate_date_range(check_in, check_out)
        total = Decimal("0.00")

        # Index inventory by date for fast lookup
        inv_by_date = {}
        if inventory_rows:
            inv_by_date = {row.date: row for row in inventory_rows}

        for d in stay_dates:
            inv_row = inv_by_date.get(d)
            nightly_price = PricingService.calculate_dynamic_price(
                room, d, inv_row,
            )
            total += nightly_price

        return round_price(total)
