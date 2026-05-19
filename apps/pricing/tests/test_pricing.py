"""
Tests for the dynamic pricing engine strategies.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.pricing.strategies import (
    HolidayPricingStrategy,
    OccupancyPricingStrategy,
    PricingContext,
    SurgePricingStrategy,
    UrgencyPricingStrategy,
    WeekendPricingStrategy,
)
from apps.pricing.services import PricingService


def make_context(**kwargs):
    """Helper to create a PricingContext with defaults."""
    defaults = {
        "room_base_price": Decimal("100.00"),
        "date": date.today() + timedelta(days=10),
        "surge_factor": Decimal("1.00"),
        "booked_count": 0,
        "total_count": 10,
        "today": date.today(),
    }
    defaults.update(kwargs)
    return PricingContext(**defaults)


class TestSurgePricingStrategy(TestCase):
    def test_no_surge(self):
        ctx = make_context(surge_factor=Decimal("1.00"))
        result = SurgePricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.00"))

    def test_with_surge(self):
        ctx = make_context(surge_factor=Decimal("1.50"))
        result = SurgePricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.50"))


class TestWeekendPricingStrategy(TestCase):
    def test_weekday_no_premium(self):
        # Find a Monday
        today = date.today()
        monday = today + timedelta(days=(7 - today.weekday()) % 7)
        ctx = make_context(date=monday)
        result = WeekendPricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.00"))

    def test_friday_premium(self):
        today = date.today()
        friday = today + timedelta(days=(4 - today.weekday()) % 7)
        if friday <= today:
            friday += timedelta(days=7)
        ctx = make_context(date=friday)
        result = WeekendPricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.20"))

    def test_saturday_premium(self):
        today = date.today()
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        if saturday <= today:
            saturday += timedelta(days=7)
        ctx = make_context(date=saturday)
        result = WeekendPricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.20"))


class TestOccupancyPricingStrategy(TestCase):
    def test_low_occupancy_no_premium(self):
        ctx = make_context(booked_count=3, total_count=10)
        result = OccupancyPricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.00"))

    def test_medium_occupancy(self):
        ctx = make_context(booked_count=7, total_count=10)
        result = OccupancyPricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.10"))

    def test_high_occupancy(self):
        ctx = make_context(booked_count=9, total_count=10)
        result = OccupancyPricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.25"))


class TestUrgencyPricingStrategy(TestCase):
    def test_same_day_premium(self):
        ctx = make_context(date=date.today(), today=date.today())
        result = UrgencyPricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.15"))

    def test_next_day_premium(self):
        ctx = make_context(date=date.today() + timedelta(days=1), today=date.today())
        result = UrgencyPricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.10"))

    def test_future_no_premium(self):
        ctx = make_context(date=date.today() + timedelta(days=10), today=date.today())
        result = UrgencyPricingStrategy().calculate_multiplier(ctx)
        self.assertEqual(result, Decimal("1.00"))
