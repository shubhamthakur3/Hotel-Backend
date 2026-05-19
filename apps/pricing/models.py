"""
Optional PricingRule model for configurable pricing rules.

These can be managed via the admin panel to add custom
holiday dates, seasonal adjustments, etc.
"""

from django.db import models


class PricingRule(models.Model):
    """
    Configurable pricing rule stored in the database.

    Used for holiday dates and seasonal pricing that
    managers can configure without code changes.
    """

    RULE_TYPES = [
        ("HOLIDAY", "Holiday"),
        ("SEASONAL", "Seasonal"),
        ("CUSTOM", "Custom"),
    ]

    name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Price multiplier (1.0 = no change, 1.3 = 30% increase).",
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pricing_rules"
        verbose_name = "Pricing Rule"
        verbose_name_plural = "Pricing Rules"
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.name} ({self.multiplier}x) [{self.start_date} - {self.end_date}]"
