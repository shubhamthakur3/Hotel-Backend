"""Serializers for payment data."""

from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment details."""

    class Meta:
        model = Payment
        fields = ["id", "transaction_id", "price", "status", "created_at", "updated_at"]
