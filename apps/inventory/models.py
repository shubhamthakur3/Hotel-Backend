"""
Inventory model — per-date availability and pricing for each room type.

This is the core data structure that enables:
- Per-day inventory control
- Dynamic nightly pricing (via surge_factor)
- Sold-out dates
- Partial room availability

Each Room gets 365 Inventory rows (one per day) when initialized.
"""

from django.db import models


class Inventory(models.Model):
    """
    Per-date inventory record for a room type.

    Fields (ER schema):
        - id: Long (PK)
        - hotel: ForeignKey → Hotel (denormalized for fast queries)
        - room: ForeignKey → Room
        - date: Date
        - booked_count: Integer (currently reserved/booked units)
        - total_count: Integer (total available units, from Room.total_count)
        - surge_factor: Decimal (pricing multiplier, default 1.0)
        - closed: Boolean (manually closed by admin)
        - created_at: Timestamp
        - updated_at: Timestamp
    """

    hotel = models.ForeignKey(
        "hotels.Hotel",
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    date = models.DateField()
    booked_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField()
    surge_factor = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text="Pricing multiplier for this date (1.0 = normal, 1.5 = 50% surge).",
    )
    closed = models.BooleanField(
        default=False,
        help_text="If True, this date is blocked from booking.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory"
        verbose_name = "Inventory"
        verbose_name_plural = "Inventory"
        unique_together = ["room", "date"]
        ordering = ["date"]
        indexes = [
            models.Index(fields=["room", "date"], name="idx_inv_room_date"),
            models.Index(fields=["hotel", "date"], name="idx_inv_hotel_date"),
            models.Index(fields=["date"], name="idx_inv_date"),
        ]

    def __str__(self):
        available = self.total_count - self.booked_count
        return f"{self.room} | {self.date} | {available}/{self.total_count} available"

    @property
    def available_count(self) -> int:
        """Number of rooms still available for booking on this date."""
        return max(0, self.total_count - self.booked_count)

    @property
    def is_available(self) -> bool:
        """Whether this date has any available rooms and is not closed."""
        return not self.closed and self.available_count > 0

    @property
    def occupancy_rate(self) -> float:
        """Occupancy rate as a percentage (0.0 to 1.0)."""
        if self.total_count == 0:
            return 0.0
        return self.booked_count / self.total_count
