"""
Serializers for Hotel and ContactInfo.
"""

from rest_framework import serializers

from .models import ContactInfo, Hotel


class ContactInfoSerializer(serializers.ModelSerializer):
    """Serializer for hotel contact information."""

    class Meta:
        model = ContactInfo
        fields = ["id", "complete_address", "location", "email", "phone_number"]


class HotelCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new hotel.
    Nested contact_info is created inline.
    """

    contact_info = ContactInfoSerializer(required=False)

    class Meta:
        model = Hotel
        fields = [
            "id", "name", "city", "description",
            "contact_info", "photos", "amenities",
            "active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "active", "created_at", "updated_at"]

    def create(self, validated_data):
        contact_data = validated_data.pop("contact_info", None)
        contact = None
        if contact_data:
            contact = ContactInfo.objects.create(**contact_data)

        hotel = Hotel.objects.create(
            contact_info=contact,
            owner=self.context["request"].user,
            **validated_data,
        )
        return hotel


class HotelUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating hotel details."""

    contact_info = ContactInfoSerializer(required=False)

    class Meta:
        model = Hotel
        fields = [
            "name", "city", "description",
            "contact_info", "photos", "amenities",
        ]

    def update(self, instance, validated_data):
        contact_data = validated_data.pop("contact_info", None)

        if contact_data:
            if instance.contact_info:
                for attr, value in contact_data.items():
                    setattr(instance.contact_info, attr, value)
                instance.contact_info.save()
            else:
                instance.contact_info = ContactInfo.objects.create(**contact_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class HotelListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for hotel lists."""

    contact_info = ContactInfoSerializer(read_only=True)

    class Meta:
        model = Hotel
        fields = [
            "id", "name", "city", "description",
            "photos", "amenities", "active",
            "contact_info", "created_at", "updated_at",
        ]


class HotelDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for a single hotel.
    Includes contact info and nested room data.
    """

    contact_info = ContactInfoSerializer(read_only=True)
    rooms = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = [
            "id", "name", "city", "description",
            "photos", "amenities", "active",
            "contact_info", "rooms",
            "created_at", "updated_at",
        ]

    def get_rooms(self, obj):
        from apps.rooms.serializers import RoomSerializer
        rooms = obj.rooms.all()
        return RoomSerializer(rooms, many=True).data


class HotelSearchResultSerializer(serializers.ModelSerializer):
    """
    Serializer for hotel search results.
    Includes minimum price for the search dates.
    """

    contact_info = ContactInfoSerializer(read_only=True)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        read_only=True, required=False,
    )

    class Meta:
        model = Hotel
        fields = [
            "id", "name", "city", "description",
            "photos", "amenities", "contact_info",
            "min_price",
        ]
