"""Serializers for inventory management."""

from rest_framework import serializers

from .models import Inventory


class InventorySerializer(serializers.ModelSerializer):
    """Read-only serializer for inventory records."""

    available_count = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    occupancy_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id", "hotel", "room", "date",
            "booked_count", "total_count",
            "available_count", "is_available", "occupancy_rate",
            "surge_factor", "closed",
            "created_at", "updated_at",
        ]


class InventoryUpdateSerializer(serializers.Serializer):
    """Serializer for bulk inventory updates."""

    date = serializers.DateField()
    surge_factor = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False,
    )
    closed = serializers.BooleanField(required=False)
    total_count = serializers.IntegerField(min_value=0, required=False)


class InventoryBulkUpdateSerializer(serializers.Serializer):
    """Wrapper serializer for bulk inventory updates."""

    updates = InventoryUpdateSerializer(many=True)
