"""
Payment model — records Stripe payment transactions.

Fields match the ER schema: id, transactionId, price, status, timestamps.
"""

from django.db import models


class PaymentStatus:
    """Payment status constants."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

    CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
    ]


class Payment(models.Model):
    """
    Payment entity — tracks Stripe payment transactions.

    Fields (ER schema):
        - id: Long (PK)
        - transaction_id: String (Stripe session/payment intent ID)
        - price: Decimal
        - status: PaymentStatus
        - created_at: Timestamp
        - updated_at: Timestamp
    """

    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Stripe Checkout Session ID or Payment Intent ID.",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.CHOICES,
        default=PaymentStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction_id"], name="idx_payment_txn"),
            models.Index(fields=["status"], name="idx_payment_status"),
        ]

    def __str__(self):
        return f"Payment #{self.id} - {self.transaction_id} ({self.status})"
