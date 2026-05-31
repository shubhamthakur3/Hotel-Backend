"""
Booking and BookingGuest models.

Implements the booking state machine:
    RESERVED → GUESTS_ADDED → PAYMENTS_PENDING → CONFIRMED
    ↓                          ↓
    EXPIRED / CANCELLED        FAILED
"""

from django.conf import settings
from django.db import models


class BookingStatus:
    """Booking state machine constants."""

    RESERVED = "RESERVED"
    GUESTS_ADDED = "GUESTS_ADDED"
    PAYMENTS_PENDING = "PAYMENTS_PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"

    CHOICES = [
        (RESERVED, "Reserved"),
        (GUESTS_ADDED, "Guests Added"),
        (PAYMENTS_PENDING, "Payment Pending"),
        (CONFIRMED, "Confirmed"),
        (CANCELLED, "Cancelled"),
        (EXPIRED, "Expired"),
        (FAILED, "Failed"),
    ]

    # Valid state transitions
    TRANSITIONS = {
        RESERVED: [GUESTS_ADDED, PAYMENTS_PENDING, CONFIRMED, CANCELLED, EXPIRED],
        GUESTS_ADDED: [PAYMENTS_PENDING, CANCELLED, EXPIRED],
        PAYMENTS_PENDING: [CONFIRMED, FAILED, CANCELLED, EXPIRED],
        CONFIRMED: [CANCELLED],  # Allow cancellation of confirmed bookings
        # Terminal states: CANCELLED, EXPIRED, FAILED — no transitions
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if a state transition is valid."""
        allowed = cls.TRANSITIONS.get(from_status, [])
        return to_status in allowed


class Booking(models.Model):
    """
    Booking entity — represents a room reservation.

    Fields (ER schema):
        - id: Long (PK)
        - hotel: ForeignKey → Hotel
        - room: ForeignKey → Room
        - user: ForeignKey → User
        - payment: OneToOne → Payment (nullable)
        - check_in_date: Date
        - checkout_date: Date
        - status: BookingStatus
        - created_at: Timestamp
        - updated_at: Timestamp
    
    Additional:
        - total_price: Decimal (calculated at booking time)
        - number_of_rooms: Integer (default 1)
    """

    hotel = models.ForeignKey(
        "hotels.Hotel",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking",
    )
    check_in_date = models.DateField()
    checkout_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.CHOICES,
        default=BookingStatus.RESERVED,
        db_index=True,
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    number_of_rooms = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bookings"
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_booking_status"),
            models.Index(fields=["user"], name="idx_booking_user"),
            models.Index(fields=["hotel"], name="idx_booking_hotel"),
            models.Index(fields=["created_at"], name="idx_booking_created"),
        ]

    def __str__(self):
        return f"Booking #{self.id} - {self.status} ({self.check_in_date} to {self.checkout_date})"

    def transition_to(self, new_status: str):
        """
        Transition the booking to a new status.
        Raises ValueError if the transition is invalid.
        """
        if not BookingStatus.can_transition(self.status, new_status):
            raise ValueError(
                f"Invalid transition: {self.status} → {new_status}"
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])


class BookingGuest(models.Model):
    """
    Through model linking Bookings to Guests.

    Fields (ER schema):
        - id: Long (PK)
        - booking: ForeignKey → Booking
        - guest: ForeignKey → Guest
    """

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="booking_guests",
    )
    guest = models.ForeignKey(
        "users.Guest",
        on_delete=models.CASCADE,
        related_name="booking_guests",
    )

    class Meta:
        db_table = "booking_guests"
        unique_together = ["booking", "guest"]
        verbose_name = "Booking Guest"
        verbose_name_plural = "Booking Guests"

    def __str__(self):
        return f"Booking #{self.booking_id} - Guest: {self.guest.name}"
