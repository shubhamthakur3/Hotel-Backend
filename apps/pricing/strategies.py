"""
Dynamic pricing strategies using the Strategy Pattern.

Each strategy is a standalone, modular pricing rule that calculates
a price multiplier. Strategies are composable — they are applied
sequentially to build the final dynamic price.

Flow:
    Base Price × Surge Factor × Weekend × Holiday × Occupancy × Urgency = Final Price
"""

import abc
import logging
from datetime import date
from decimal import Decimal
from typing import NamedTuple

logger = logging.getLogger(__name__)


class PricingContext(NamedTuple):
    """
    Context object passed to each pricing strategy.

    Contains all data a strategy might need to calculate its multiplier.
    """

    room_base_price: Decimal
    date: date
    surge_factor: Decimal  # From inventory record
    booked_count: int
    total_count: int
    today: date


class PricingStrategy(abc.ABC):
    """Base class for all pricing strategies."""

    @abc.abstractmethod
    def calculate_multiplier(self, context: PricingContext) -> Decimal:
        """
        Calculate the price multiplier for this strategy.

        Returns:
            Decimal: Multiplier (1.0 = no change, 1.2 = 20% increase)
        """
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__


class SurgePricingStrategy(PricingStrategy):
    """
    Apply the surge factor from the inventory record.

    The surge_factor is set by hotel managers on individual
    inventory days (e.g., 1.5 for a big event weekend).
    """

    def calculate_multiplier(self, context: PricingContext) -> Decimal:
        return context.surge_factor


class WeekendPricingStrategy(PricingStrategy):
    """
    Apply a weekend premium for Friday and Saturday nights.

    Friday (4) and Saturday (5) are considered weekend nights
    where demand is typically higher.
    """

    WEEKEND_PREMIUM = Decimal("1.20")  # 20% increase

    def calculate_multiplier(self, context: PricingContext) -> Decimal:
        if context.date.weekday() in (4, 5):
            return self.WEEKEND_PREMIUM
        return Decimal("1.00")


class HolidayPricingStrategy(PricingStrategy):
    """
    Apply holiday pricing from database PricingRule records.

    Checks if the date falls within any active holiday/seasonal
    pricing rule and returns the configured multiplier.
    """

    def calculate_multiplier(self, context: PricingContext) -> Decimal:
        from .models import PricingRule

        rules = PricingRule.objects.filter(
            is_active=True,
            start_date__lte=context.date,
            end_date__gte=context.date,
        )

        # Apply the highest multiplier if multiple rules overlap
        max_multiplier = Decimal("1.00")
        for rule in rules:
            if rule.multiplier > max_multiplier:
                max_multiplier = rule.multiplier

        return max_multiplier


class OccupancyPricingStrategy(PricingStrategy):
    """
    Premium based on how full the hotel is for a given date.

    Tiers:
        - >80% occupancy → 25% premium
        - >60% occupancy → 10% premium
        - Otherwise → no change
    """

    def calculate_multiplier(self, context: PricingContext) -> Decimal:
        if context.total_count == 0:
            return Decimal("1.00")

        occupancy = context.booked_count / context.total_count

        if occupancy > 0.80:
            return Decimal("1.25")
        elif occupancy > 0.60:
            return Decimal("1.10")
        return Decimal("1.00")


class UrgencyPricingStrategy(PricingStrategy):
    """
    Premium for last-minute / same-day bookings.

    If the booking date is today or tomorrow, apply urgency pricing.
    """

    def calculate_multiplier(self, context: PricingContext) -> Decimal:
        days_until = (context.date - context.today).days

        if days_until <= 0:
            return Decimal("1.15")  # 15% same-day premium
        elif days_until <= 1:
            return Decimal("1.10")  # 10% next-day premium
        return Decimal("1.00")
