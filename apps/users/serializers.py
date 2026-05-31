"""Serializers for user profile and guest management."""

from rest_framework import serializers

from apps.accounts.serializers import UserProfileSerializer, UserProfileUpdateSerializer

from .models import Guest


class GuestSerializer(serializers.ModelSerializer):
    """Serializer for guest CRUD."""

    class Meta:
        model = Guest
        fields = ["id", "name", "gender", "created_at", "hotel"]
        read_only_fields = ["id", "created_at", "hotel"]


class GuestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a guest."""
    hotel_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Guest
        fields = ["name", "gender", "hotel_id"]

    def create(self, validated_data):
        hotel_id = validated_data.pop("hotel_id")
        validated_data["hotel_id"] = hotel_id
        validated_data["user"] = self.context["request"].user
        return Guest.objects.create(**validated_data)
