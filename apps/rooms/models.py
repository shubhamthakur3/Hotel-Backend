"""
Room model — represents a room type within a hotel.

Each Room is not a single physical room but a *type* of room
(e.g., "Deluxe King") with a total_count of available units.
Individual per-day availability is tracked by Inventory records.
"""

from django.db import models


class RoomType:
    """Room type constants."""

    STANDARD = "STANDARD"
    DELUXE = "DELUXE"
    SUITE = "SUITE"

    CHOICES = [
        (STANDARD, "Standard"),
        (DELUXE, "Deluxe"),
        (SUITE, "Suite"),
    ]


class Room(models.Model):
    """
    Room entity (room type within a hotel).

    Fields (ER schema):
        - id: Long (PK)
        - hotel: ForeignKey → Hotel
        - type: String (STANDARD, DELUXE, SUITE)
        - base_price: Decimal
        - amenities: Text[] (JSON)
        - photos: Text[] (JSON)
        - total_count: Integer (number of physical units of this type)
        - capacity: Integer (max occupancy per unit)
        - created_at: Timestamp
        - updated_at: Timestamp
    """

    hotel = models.ForeignKey(
        "hotels.Hotel",
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    type = models.CharField(
        max_length=20,
        choices=RoomType.CHOICES,
        default=RoomType.STANDARD,
    )
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    amenities = models.JSONField(default=list, blank=True)
    photos = models.JSONField(default=list, blank=True)
    total_count = models.PositiveIntegerField(
        help_text="Number of physical rooms of this type in the hotel."
    )
    capacity = models.PositiveIntegerField(
        help_text="Maximum number of guests per room unit."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rooms"
        verbose_name = "Room"
        verbose_name_plural = "Rooms"
        ordering = ["type", "base_price"]
        indexes = [
            models.Index(fields=["hotel"], name="idx_room_hotel"),
            models.Index(fields=["type"], name="idx_room_type"),
        ]

    def __str__(self):
        return f"{self.get_type_display()} @ {self.hotel.name} (${self.base_price})"
