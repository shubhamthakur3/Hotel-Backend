"""
Room admin views — CRUD for rooms under a hotel.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrManager

from .models import Room
from .serializers import RoomCreateSerializer, RoomSerializer, RoomUpdateSerializer
from .services import RoomService

logger = logging.getLogger(__name__)


class RoomListCreateView(APIView):
    """
    GET  /api/admin/hotels/{hotelId}/rooms      — List rooms
    POST /api/admin/hotels/{hotelId}/rooms      — Create room
    """

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request, hotel_id):
        from apps.hotels.services import HotelService

        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, request.user)

        rooms = Room.objects.filter(hotel=hotel)
        serializer = RoomSerializer(rooms, many=True)
        return Response(serializer.data)

    def post(self, request, hotel_id):
        serializer = RoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room = RoomService.create_room(
            hotel_id=hotel_id,
            data=serializer.validated_data,
            user=request.user,
        )
        return Response(
            RoomSerializer(room).data,
            status=status.HTTP_201_CREATED,
        )


class RoomDetailView(APIView):
    """
    GET    /api/admin/hotels/{hotelId}/rooms/{roomId}   — Room detail
    PUT    /api/admin/hotels/{hotelId}/rooms/{roomId}   — Update room
    DELETE /api/admin/hotels/{hotelId}/rooms/{roomId}   — Delete room
    """

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request, hotel_id, room_id):
        from apps.hotels.services import HotelService

        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, request.user)
        room = RoomService.get_room_or_404(room_id, hotel_id)
        return Response(RoomSerializer(room).data)

    def put(self, request, hotel_id, room_id):
        serializer = RoomUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        room = RoomService.update_room(
            hotel_id=hotel_id,
            room_id=room_id,
            data=serializer.validated_data,
            user=request.user,
        )
        return Response(RoomSerializer(room).data)

    def delete(self, request, hotel_id, room_id):
        RoomService.delete_room(hotel_id, room_id, request.user)
        return Response(
            {"message": "Room deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
