"""Serializers for Room management."""

from rest_framework import serializers

from .models import Room, RoomType


class RoomSerializer(serializers.ModelSerializer):
    """Read-only serializer for room data."""

    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Room
        fields = [
            "id", "hotel", "type", "type_display",
            "base_price", "amenities", "photos",
            "total_count", "capacity",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "hotel", "created_at", "updated_at"]


class RoomCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a room under a hotel."""

    class Meta:
        model = Room
        fields = [
            "id", "type", "base_price", "amenities", "photos",
            "total_count", "capacity",
        ]
        read_only_fields = ["id"]

    def validate_base_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Base price must be positive.")
        return value

    def validate_total_count(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total count must be at least 1.")
        return value

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be at least 1.")
        return value


class RoomUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating room details."""

    class Meta:
        model = Room
        fields = [
            "type", "base_price", "amenities", "photos",
            "total_count", "capacity",
        ]
