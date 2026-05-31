"""
User profile and guest management views.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import UserProfileSerializer, UserProfileUpdateSerializer
from apps.bookings.models import Booking
from apps.bookings.serializers import BookingListSerializer
from apps.common.exceptions import ResourceNotFoundException
from apps.common.pagination import StandardResultsPagination

from .models import Guest
from .serializers import GuestCreateSerializer, GuestSerializer

logger = logging.getLogger(__name__)


class UserProfileView(APIView):
    """
    GET   /api/users/profile  — Get my profile
    PATCH /api/users/profile  — Update my profile
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(request.user).data)


class MyBookingsView(APIView):
    """
    GET /api/users/myBookings  — Get my bookings
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(
            user=request.user
        ).select_related("hotel", "room").order_by("-created_at")

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(bookings, request)
        serializer = BookingListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class GuestListCreateView(APIView):
    """
    GET  /api/users/guests  — List my guests
    POST /api/users/guests  — Add a guest (Hotel Manager / Admin only, for their own hotel)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        guests = Guest.objects.filter(user=request.user)
        serializer = GuestSerializer(guests, many=True)
        return Response(serializer.data)

    def post(self, request):
        from apps.accounts.models import UserRole
        from apps.hotels.models import Hotel

        if not (request.user.has_role(UserRole.HOTEL_MANAGER) or request.user.has_role(UserRole.ADMIN)):
            return Response(
                {"error": {"code": "forbidden", "message": "Only hotel managers can create guest profiles."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = GuestCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        hotel_id = serializer.validated_data.get("hotel_id")
        try:
            hotel = Hotel.objects.get(id=hotel_id)
        except Hotel.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": f"Hotel with id {hotel_id} not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Enforce that HOTEL_MANAGER can only create guests for their own property
        if not request.user.has_role(UserRole.ADMIN) and hotel.owner != request.user:
            return Response(
                {"error": {"code": "forbidden", "message": "You can only create guest profiles for your own hotels."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        guest = serializer.save()
        return Response(
            GuestSerializer(guest).data,
            status=status.HTTP_201_CREATED,
        )


class GuestDetailView(APIView):
    """
    PUT    /api/users/guests/{guestId}  — Update a guest
    DELETE /api/users/guests/{guestId}  — Remove a guest
    """

    permission_classes = [IsAuthenticated]

    def _get_guest(self, guest_id, user):
        try:
            return Guest.objects.get(id=guest_id, user=user)
        except Guest.DoesNotExist:
            raise ResourceNotFoundException(f"Guest with id {guest_id} not found.")

    def put(self, request, guest_id):
        guest = self._get_guest(guest_id, request.user)
        serializer = GuestSerializer(guest, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, guest_id):
        guest = self._get_guest(guest_id, request.user)
        guest.delete()
        return Response(
            {"message": "Guest removed successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
