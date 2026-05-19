"""
Hotel admin views — CRUD operations for hotel managers/admins.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrManager
from apps.common.pagination import StandardResultsPagination

from .models import Hotel
from .serializers import (
    HotelCreateSerializer,
    HotelDetailSerializer,
    HotelListSerializer,
    HotelUpdateSerializer,
)
from .services import HotelService

logger = logging.getLogger(__name__)


class HotelAdminListCreateView(APIView):
    """
    GET  /api/admin/hotels          — List all hotels owned by the manager
    POST /api/admin/hotels          — Create a new hotel
    """

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        """List all hotels owned by the current manager."""
        from apps.accounts.models import UserRole

        if request.user.has_role(UserRole.ADMIN):
            hotels = Hotel.objects.all().select_related("contact_info")
        else:
            hotels = Hotel.objects.filter(owner=request.user).select_related("contact_info")

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(hotels, request)
        serializer = HotelListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create a new hotel (inactive by default)."""
        serializer = HotelCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        hotel = serializer.save()
        logger.info("Hotel created: %s by %s", hotel.name, request.user.email)
        return Response(
            HotelDetailSerializer(hotel).data,
            status=status.HTTP_201_CREATED,
        )


class HotelAdminDetailView(APIView):
    """
    GET    /api/admin/hotels/{hotelId}          — Get hotel details
    PUT    /api/admin/hotels/{hotelId}          — Update hotel
    DELETE /api/admin/hotels/{hotelId}          — Delete hotel
    """

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request, hotel_id):
        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, request.user)
        serializer = HotelDetailSerializer(hotel)
        return Response(serializer.data)

    def put(self, request, hotel_id):
        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, request.user)

        serializer = HotelUpdateSerializer(hotel, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        hotel = serializer.save()

        logger.info("Hotel updated: %s (id=%d)", hotel.name, hotel.id)
        return Response(HotelDetailSerializer(hotel).data)

    def delete(self, request, hotel_id):
        HotelService.delete_hotel(hotel_id, request.user)
        return Response(
            {"message": "Hotel deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


class HotelActivateView(APIView):
    """
    PATCH /api/admin/hotels/{hotelId}/activate — Activate a hotel
    """

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def patch(self, request, hotel_id):
        hotel = HotelService.activate_hotel(hotel_id, request.user)
        return Response(
            {
                "message": f"Hotel '{hotel.name}' has been activated.",
                "hotel": HotelDetailSerializer(hotel).data,
            }
        )
