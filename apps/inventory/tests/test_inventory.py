"""Tests for inventory initialization and management."""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.hotels.models import Hotel
from apps.inventory.models import Inventory
from apps.inventory.services import InventoryService
from apps.rooms.models import Room


class TestInventoryInitialization(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            email="m@test.com", password="Pass123!", name="M",
            roles=[UserRole.HOTEL_MANAGER],
        )
        self.hotel = Hotel.objects.create(
            name="Test", city="NYC", active=True, owner=self.manager,
        )
        self.room = Room.objects.create(
            hotel=self.hotel, type="STANDARD",
            base_price=Decimal("100.00"), total_count=5, capacity=2,
        )

    def test_initialize_creates_365_records(self):
        count = InventoryService.initialize_room_for_a_year(self.room)
        self.assertEqual(Inventory.objects.filter(room=self.room).count(), 365)

    def test_initialize_sets_correct_total_count(self):
        InventoryService.initialize_room_for_a_year(self.room)
        inv = Inventory.objects.filter(room=self.room).first()
        self.assertEqual(inv.total_count, 5)
        self.assertEqual(inv.booked_count, 0)

    def test_reinitialize_is_idempotent(self):
        InventoryService.initialize_room_for_a_year(self.room)
        InventoryService.initialize_room_for_a_year(self.room)
        self.assertEqual(Inventory.objects.filter(room=self.room).count(), 365)

    def test_available_count_property(self):
        InventoryService.initialize_room_for_a_year(self.room)
        inv = Inventory.objects.filter(room=self.room).first()
        self.assertEqual(inv.available_count, 5)
        inv.booked_count = 3
        inv.save()
        self.assertEqual(inv.available_count, 2)

    def test_closed_inventory_not_available(self):
        InventoryService.initialize_room_for_a_year(self.room)
        inv = Inventory.objects.filter(room=self.room).first()
        inv.closed = True
        inv.save()
        self.assertFalse(inv.is_available)
