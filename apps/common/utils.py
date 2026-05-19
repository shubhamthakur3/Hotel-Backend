"""
Shared utility functions for the Hotel Backend API.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import List


def generate_date_range(start_date: date, end_date: date) -> List[date]:
    """
    Generate a list of dates from start_date (inclusive) to end_date (exclusive).

    Args:
        start_date: The check-in date (inclusive).
        end_date: The check-out date (exclusive, as guests leave on this day).

    Returns:
        List of date objects for each night of the stay.
    """
    dates = []
    current = start_date
    while current < end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def round_price(price: Decimal) -> Decimal:
    """Round a price to 2 decimal places using banker's rounding."""
    return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_weekend(d: date) -> bool:
    """Check if a date falls on a weekend (Friday or Saturday night)."""
    return d.weekday() in (4, 5)  # Friday=4, Saturday=5


def calculate_nights(check_in: date, check_out: date) -> int:
    """Calculate the number of nights between check-in and check-out."""
    return (check_out - check_in).days
