"""Serializers for user profile and guest management."""

from rest_framework import serializers

from apps.accounts.serializers import UserProfileSerializer, UserProfileUpdateSerializer

from .models import Guest


class GuestSerializer(serializers.ModelSerializer):
    """Serializer for guest CRUD."""

    class Meta:
        model = Guest
        fields = ["id", "name", "gender", "created_at"]
        read_only_fields = ["id", "created_at"]


class GuestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a guest."""

    class Meta:
        model = Guest
        fields = ["name", "gender"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return Guest.objects.create(**validated_data)
