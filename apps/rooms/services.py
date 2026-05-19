"""
Room service layer.

Handles room creation (which triggers inventory initialization)
and room management business logic.
"""

import logging

from apps.common.exceptions import ResourceNotFoundException
from apps.hotels.services import HotelService

from .models import Room

logger = logging.getLogger(__name__)


class RoomService:
    """Business logic for room operations."""

    @staticmethod
    def get_room_or_404(room_id: int, hotel_id: int = None) -> Room:
        """Retrieve a room by ID, optionally scoped to a hotel."""
        try:
            filters = {"id": room_id}
            if hotel_id:
                filters["hotel_id"] = hotel_id
            return Room.objects.select_related("hotel").get(**filters)
        except Room.DoesNotExist:
            raise ResourceNotFoundException(f"Room with id {room_id} not found.")

    @staticmethod
    def create_room(hotel_id: int, data: dict, user) -> Room:
        """
        Create a room under a hotel.
        If the hotel is active, also initializes inventory for 365 days.
        """
        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, user)

        room = Room.objects.create(hotel=hotel, **data)
        logger.info(
            "Room created: %s (id=%d) for hotel %s",
            room.get_type_display(), room.id, hotel.name,
        )

        # If hotel is active, generate inventory immediately
        if hotel.active:
            from apps.inventory.services import InventoryService
            InventoryService.initialize_room_for_a_year(room)

        return room

    @staticmethod
    def update_room(hotel_id: int, room_id: int, data: dict, user) -> Room:
        """Update room details."""
        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, user)
        room = RoomService.get_room_or_404(room_id, hotel_id)

        for attr, value in data.items():
            setattr(room, attr, value)
        room.save()

        logger.info("Room updated: id=%d", room.id)
        return room

    @staticmethod
    def delete_room(hotel_id: int, room_id: int, user) -> None:
        """Delete a room and its associated inventory."""
        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, user)
        room = RoomService.get_room_or_404(room_id, hotel_id)
        room.delete()
        logger.info("Room deleted: id=%d from hotel %s", room_id, hotel.name)
