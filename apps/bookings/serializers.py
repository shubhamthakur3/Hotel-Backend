"""Serializers for booking endpoints."""

from rest_framework import serializers

from .models import Booking, BookingGuest, BookingStatus


class BookingInitSerializer(serializers.Serializer):
    """Serializer for booking initialization request."""

    room_id = serializers.IntegerField()
    check_in_date = serializers.DateField()
    checkout_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["check_in_date"] >= attrs["checkout_date"]:
            raise serializers.ValidationError(
                "Check-out date must be after check-in date."
            )
        return attrs


class BookingGuestAddSerializer(serializers.Serializer):
    """Serializer for adding guests to a booking."""

    guest_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )


class BookingGuestSerializer(serializers.ModelSerializer):
    """Serializer for booking guest details."""

    guest_name = serializers.CharField(source="guest.name", read_only=True)
    guest_gender = serializers.CharField(source="guest.gender", read_only=True)

    class Meta:
        model = BookingGuest
        fields = ["id", "guest", "guest_name", "guest_gender"]


class BookingSerializer(serializers.ModelSerializer):
    """Full serializer for booking details."""

    hotel_name = serializers.CharField(source="hotel.name", read_only=True)
    room_type = serializers.CharField(source="room.get_type_display", read_only=True)
    guests = BookingGuestSerializer(source="booking_guests", many=True, read_only=True)
    payment_status = serializers.CharField(
        source="payment.status", read_only=True, default=None,
    )

    class Meta:
        model = Booking
        fields = [
            "id", "hotel", "hotel_name",
            "room", "room_type",
            "user", "check_in_date", "checkout_date",
            "status", "total_price", "number_of_rooms",
            "guests", "payment_status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "total_price", "created_at", "updated_at"]


class BookingStatusSerializer(serializers.ModelSerializer):
    """Lightweight serializer for booking status checks."""

    class Meta:
        model = Booking
        fields = ["id", "status", "total_price", "created_at", "updated_at"]


class BookingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for booking lists."""

    hotel_name = serializers.CharField(source="hotel.name", read_only=True)
    room_type = serializers.CharField(source="room.get_type_display", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "hotel_name", "room_type",
            "check_in_date", "checkout_date",
            "status", "total_price",
            "created_at",
        ]
