"""
Guest model — saved guest profiles belonging to a user.

Guests are stored independently and can be attached to
multiple bookings via the BookingGuest through table.
"""

from django.conf import settings
from django.db import models


class GenderChoice:
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

    CHOICES = [
        (MALE, "Male"),
        (FEMALE, "Female"),
        (OTHER, "Other"),
    ]


class Guest(models.Model):
    """
    Guest entity — a saved traveller profile.

    Fields (ER schema):
        - id: Long (PK)
        - user: ForeignKey → User (owner)
        - name: String
        - created_at: Timestamp
        - gender: Gender enum
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guests",
    )
    hotel = models.ForeignKey(
        "hotels.Hotel",
        on_delete=models.CASCADE,
        related_name="guests",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    gender = models.CharField(
        max_length=10,
        choices=GenderChoice.CHOICES,
        default=GenderChoice.OTHER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "guests"
        verbose_name = "Guest"
        verbose_name_plural = "Guests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"
