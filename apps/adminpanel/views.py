"""
Admin panel views — hotel booking reports and management.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrManager
from apps.bookings.models import Booking, BookingStatus
from apps.bookings.serializers import BookingListSerializer
from apps.common.pagination import StandardResultsPagination
from apps.hotels.services import HotelService

logger = logging.getLogger(__name__)


class HotelBookingsListView(APIView):
    """
    GET /api/admin/hotels/{hotelId}/bookings

    List all bookings for a specific hotel.
    Supports filtering by status and date range.
    """

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request, hotel_id):
        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, request.user)

        bookings = Booking.objects.filter(
            hotel=hotel
        ).select_related("room", "user").order_by("-created_at")

        # Filter by status
        status_filter = request.query_params.get("status")
        if status_filter:
            bookings = bookings.filter(status=status_filter)

        # Filter by date range
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        if from_date:
            bookings = bookings.filter(check_in_date__gte=from_date)
        if to_date:
            bookings = bookings.filter(checkout_date__lte=to_date)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(bookings, request)
        serializer = BookingListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class HotelReportView(APIView):
    """
    GET /api/admin/hotels/{hotelId}/reports

    Generate a booking report for a hotel.

    Returns:
        - Total bookings by status
        - Total revenue (confirmed bookings)
        - Average booking value
        - Occupancy stats for the next 30 days
        - Top room types
    """

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request, hotel_id):
        hotel = HotelService.get_hotel_or_404(hotel_id)
        HotelService.verify_hotel_ownership(hotel, request.user)

        bookings = Booking.objects.filter(hotel=hotel)

        # Bookings by status
        status_counts = (
            bookings.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        status_summary = {item["status"]: item["count"] for item in status_counts}

        # Revenue from confirmed bookings
        confirmed = bookings.filter(status=BookingStatus.CONFIRMED)
        total_revenue = confirmed.aggregate(
            total=Sum("total_price")
        )["total"] or Decimal("0.00")

        confirmed_count = confirmed.count()
        avg_booking_value = (
            total_revenue / confirmed_count if confirmed_count > 0 else Decimal("0.00")
        )

        # Room type popularity
        room_stats = (
            bookings.filter(status=BookingStatus.CONFIRMED)
            .values("room__type")
            .annotate(count=Count("id"), revenue=Sum("total_price"))
            .order_by("-count")
        )

        # Upcoming bookings (next 30 days)
        today = date.today()
        upcoming = bookings.filter(
            check_in_date__gte=today,
            check_in_date__lte=today + timedelta(days=30),
            status__in=[BookingStatus.CONFIRMED, BookingStatus.PAYMENTS_PENDING],
        ).count()

        return Response(
            {
                "hotel_id": hotel.id,
                "hotel_name": hotel.name,
                "report": {
                    "total_bookings": bookings.count(),
                    "bookings_by_status": status_summary,
                    "total_revenue": str(total_revenue),
                    "confirmed_bookings": confirmed_count,
                    "average_booking_value": str(avg_booking_value.quantize(Decimal("0.01"))),
                    "upcoming_bookings_30d": upcoming,
                    "room_type_stats": list(room_stats),
                },
            }
        )


class ManualConfirmBookingView(APIView):
    """
    POST /api/admin/bookings/{bookingId}/manual-confirm

    Allows hotel managers / admin / lobby staff to manually confirm
    a booking when the guest pays via Cash or POS at the front desk.

    This bypasses the Stripe webhook flow entirely.

    Request body (all optional):
    {
        "payment_method": "CASH",  // CASH | POS | BANK_TRANSFER (default: CASH)
        "notes": "Guest paid at front desk"
    }
    """

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def post(self, request, booking_id):
        from apps.bookings.services import BookingService
        from apps.bookings.serializers import BookingSerializer

        payment_method = request.data.get("payment_method", "CASH").upper()
        notes = request.data.get("notes", "")

        # Validate payment_method
        allowed_methods = ["CASH", "POS", "BANK_TRANSFER"]
        if payment_method not in allowed_methods:
            return Response(
                {
                    "error": {
                        "code": "invalid_payment_method",
                        "message": f"Invalid payment method. Allowed: {', '.join(allowed_methods)}",
                    }
                },
                status=400,
            )

        booking = BookingService.manual_confirm_booking(
            booking_id=booking_id,
            confirmed_by_user=request.user,
            payment_method=payment_method,
            notes=notes,
        )

        logger.info(
            "Manual confirmation by %s for booking #%d (method=%s)",
            request.user.email, booking_id, payment_method,
        )

        return Response(
            {
                "message": f"Booking #{booking.id} manually confirmed ({payment_method}).",
                "booking": BookingSerializer(booking).data,
            }
        )

