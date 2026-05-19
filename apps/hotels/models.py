"""
Hotel and ContactInfo models.

Matches the ER schema provided. Hotels are owned by managers
and start inactive until explicitly activated.
"""

from django.conf import settings
from django.db import models


class ContactInfo(models.Model):
    """
    Contact information for a hotel.

    Fields (ER schema):
        - id: Long (PK)
        - complete_address: String
        - location: String
        - email: String
        - phone_number: String
    """

    complete_address = models.TextField()
    location = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        db_table = "contact_info"
        verbose_name = "Contact Info"
        verbose_name_plural = "Contact Info"

    def __str__(self):
        return f"Contact: {self.email or self.phone_number}"


class Hotel(models.Model):
    """
    Hotel entity.

    Fields (ER schema):
        - id: Long (PK)
        - city: String (indexed for search)
        - contact_info: OneToOne → ContactInfo
        - photos: Text[] (JSON list of URLs)
        - amenities: Text[] (JSON list)
        - created_at: Timestamp
        - updated_at: Timestamp
        - active: Boolean (default False, activated by admin/manager)
    
    Additional:
        - name: Hotel name (for display)
        - description: Text description
        - owner: ForeignKey → User (hotel manager)
    """

    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True, default="")
    contact_info = models.OneToOneField(
        ContactInfo,
        on_delete=models.CASCADE,
        related_name="hotel",
        null=True,
        blank=True,
    )
    photos = models.JSONField(default=list, blank=True)
    amenities = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hotels",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hotels"
        verbose_name = "Hotel"
        verbose_name_plural = "Hotels"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["city"], name="idx_hotel_city"),
            models.Index(fields=["active"], name="idx_hotel_active"),
            models.Index(fields=["owner"], name="idx_hotel_owner"),
        ]

    def __str__(self):
        return f"{self.name} ({self.city})"


class HotelMinPrice(models.Model):
    """
    Precomputed minimum room price per hotel per date.

    Used for fast search queries — avoids expensive joins
    against the full Inventory table during hotel search.

    Updated hourly by the pricing background task.
    """

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name="min_prices",
    )
    date = models.DateField()
    min_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "hotel_min_prices"
        unique_together = ["hotel", "date"]
        indexes = [
            models.Index(fields=["hotel", "date"], name="idx_hmp_hotel_date"),
            models.Index(fields=["date", "min_price"], name="idx_hmp_date_price"),
        ]

    def __str__(self):
        return f"{self.hotel.name} on {self.date}: ${self.min_price}"
