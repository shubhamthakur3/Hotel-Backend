"""
Hotel service layer.

Contains business logic for hotel management and search,
keeping views thin.
"""

import logging
from datetime import date
from decimal import Decimal

from django.db import models
from django.db.models import Count, Min, OuterRef, Q, Subquery

from apps.common.exceptions import ForbiddenException, ResourceNotFoundException

from .models import Hotel, HotelMinPrice

logger = logging.getLogger(__name__)


class HotelService:
    """Business logic for hotel operations."""

    @staticmethod
    def get_hotel_or_404(hotel_id: int) -> Hotel:
        """Retrieve a hotel by ID or raise 404."""
        try:
            return Hotel.objects.select_related("contact_info").get(id=hotel_id)
        except Hotel.DoesNotExist:
            raise ResourceNotFoundException(f"Hotel with id {hotel_id} not found.")

    @staticmethod
    def verify_hotel_ownership(hotel: Hotel, user) -> None:
        """Verify that the user owns this hotel (or is admin)."""
        from apps.accounts.models import UserRole

        if user.has_role(UserRole.ADMIN):
            return
        if hotel.owner != user:
            raise ForbiddenException("You do not own this hotel.")

    @staticmethod
    def activate_hotel(hotel_id: int, user) -> Hotel:
        """
        Activate a hotel. Only the owner or admin can activate.
        Also triggers inventory initialization for all rooms.
        """
        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, user)

        if hotel.active:
            return hotel

        hotel.active = True
        hotel.save(update_fields=["active", "updated_at"])

        # Initialize inventory for all rooms
        from apps.inventory.services import InventoryService
        for room in hotel.rooms.all():
            InventoryService.initialize_room_for_a_year(room)

        logger.info("Hotel activated: %s (id=%d)", hotel.name, hotel.id)
        return hotel

    @staticmethod
    def search_hotels(
        city: str = None,
        check_in: date = None,
        check_out: date = None,
        guests: int = None,
        min_price: Decimal = None,
        max_price: Decimal = None,
        amenities: list = None,
    ):
        """
        Search for available hotels.

        Uses HotelMinPrice for fast filtering, then checks
        actual inventory availability.
        """
        queryset = Hotel.objects.filter(active=True).select_related("contact_info")

        # Filter by city
        if city:
            queryset = queryset.filter(city__icontains=city)

        # Filter by amenities (JSON array contains)
        if amenities:
            for amenity in amenities:
                queryset = queryset.filter(amenities__contains=[amenity])

        # Filter by guest capacity (at least one room can accommodate)
        if guests:
            queryset = queryset.filter(rooms__capacity__gte=guests).distinct()

        # Filter by date availability and price using HotelMinPrice
        if check_in and check_out:
            from apps.common.utils import generate_date_range
            stay_dates = generate_date_range(check_in, check_out)

            if stay_dates:
                # Find hotels that have min_price records for ALL stay dates
                hotel_ids_with_availability = (
                    HotelMinPrice.objects.filter(
                        date__in=stay_dates,
                    )
                    .values("hotel_id")
                    .annotate(date_count=Count("date", distinct=True))
                    .filter(date_count=len(stay_dates))
                    .values_list("hotel_id", flat=True)
                )
                queryset = queryset.filter(id__in=hotel_ids_with_availability)

                # Add min_price annotation for the stay period
                price_subquery = HotelMinPrice.objects.filter(
                    hotel=OuterRef("pk"),
                    date__in=stay_dates,
                ).values("hotel").annotate(
                    lowest=Min("min_price")
                ).values("lowest")[:1]

                queryset = queryset.annotate(
                    min_price=Subquery(price_subquery)
                )

                # Filter by price range
                if min_price is not None:
                    queryset = queryset.filter(min_price__gte=min_price)
                if max_price is not None:
                    queryset = queryset.filter(min_price__lte=max_price)

        return queryset

    @staticmethod
    def delete_hotel(hotel_id: int, user) -> None:
        """Delete a hotel. Only the owner or admin can delete."""
        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, user)
        hotel_name = hotel.name
        hotel.delete()
        logger.info("Hotel deleted: %s (id=%d)", hotel_name, hotel_id)

