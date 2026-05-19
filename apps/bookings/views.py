"""
Booking views — handles the full booking lifecycle.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttles import BookingRateThrottle

from .serializers import (
    BookingGuestAddSerializer,
    BookingInitSerializer,
    BookingSerializer,
    BookingStatusSerializer,
)
from .services import BookingService

logger = logging.getLogger(__name__)


class BookingInitView(APIView):
    """
    POST /api/bookings/init

    Initialize a new booking (reserve inventory).
    This is Step 1 of the booking flow.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [BookingRateThrottle]

    def post(self, request):
        serializer = BookingInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = BookingService.initialize_booking(
            user=request.user,
            room_id=serializer.validated_data["room_id"],
            check_in=serializer.validated_data["check_in_date"],
            check_out=serializer.validated_data["checkout_date"],
        )

        return Response(
            {
                "message": "Booking reserved successfully. Please add guests and proceed to payment.",
                "booking": BookingSerializer(booking).data,
            },
            status=status.HTTP_201_CREATED,
        )


class BookingAddGuestsView(APIView):
    """
    POST /api/bookings/{bookingId}/addGuests

    Add guests to a booking (Step 2).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        serializer = BookingGuestAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = BookingService.add_guests(
            booking_id=booking_id,
            guest_ids=serializer.validated_data["guest_ids"],
            user=request.user,
        )

        return Response(
            {
                "message": "Guests added successfully.",
                "booking": BookingSerializer(booking).data,
            }
        )


class BookingPaymentView(APIView):
    """
    POST /api/bookings/{bookingId}/payments

    Initiate payment via Stripe Checkout (Step 3).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        from apps.payments.services import CheckoutService

        booking = BookingService.get_booking_or_404(booking_id)

        if booking.user != request.user:
            return Response(
                {"error": {"code": "forbidden", "message": "You do not own this booking."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        checkout_data = CheckoutService.create_checkout_session(booking)

        return Response(
            {
                "message": "Stripe checkout session created.",
                "session_url": checkout_data["session_url"],
                "session_id": checkout_data["session_id"],
                "booking": BookingSerializer(booking).data,
            }
        )


class BookingCancelView(APIView):
    """
    POST /api/bookings/{bookingId}/cancel

    Cancel a booking and release inventory.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        booking = BookingService.cancel_booking(booking_id, request.user)

        return Response(
            {
                "message": "Booking cancelled successfully.",
                "booking": BookingSerializer(booking).data,
            }
        )


class BookingStatusView(APIView):
    """
    GET /api/bookings/{bookingId}/status

    Check the current status of a booking.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        booking = BookingService.get_booking_or_404(booking_id)

        if booking.user != request.user:
            return Response(
                {"error": {"code": "forbidden", "message": "You do not own this booking."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(BookingStatusSerializer(booking).data)
