"""
Hotel browse views — public/authenticated search and detail endpoints.
"""

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsPagination

from .models import Hotel
from .serializers import HotelDetailSerializer, HotelSearchResultSerializer
from .services import HotelService

logger = logging.getLogger(__name__)


class HotelSearchView(APIView):
    """
    GET /api/hotels/search

    Search for available hotels with filters:
        - city: City name (partial match)
        - check_in: Check-in date (YYYY-MM-DD)
        - check_out: Check-out date (YYYY-MM-DD)
        - guests: Number of guests
        - min_price: Minimum price filter
        - max_price: Maximum price filter
        - amenities: Comma-separated list of amenities
    """

    permission_classes = [AllowAny]

    def get(self, request):
        city = request.query_params.get("city")
        check_in_str = request.query_params.get("check_in")
        check_out_str = request.query_params.get("check_out")
        guests_str = request.query_params.get("guests")
        min_price_str = request.query_params.get("min_price")
        max_price_str = request.query_params.get("max_price")
        amenities_str = request.query_params.get("amenities")

        # Parse dates
        check_in = None
        check_out = None
        if check_in_str:
            try:
                check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": {"code": "invalid_date", "message": "Invalid check_in date format. Use YYYY-MM-DD."}},
                    status=400,
                )
        if check_out_str:
            try:
                check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": {"code": "invalid_date", "message": "Invalid check_out date format. Use YYYY-MM-DD."}},
                    status=400,
                )

        # Validate date range
        if check_in and check_out and check_in >= check_out:
            return Response(
                {"error": {"code": "invalid_date_range", "message": "check_out must be after check_in."}},
                status=400,
            )

        # Parse numbers
        guests = int(guests_str) if guests_str else None
        try:
            min_price = Decimal(min_price_str) if min_price_str else None
            max_price = Decimal(max_price_str) if max_price_str else None
        except InvalidOperation:
            return Response(
                {"error": {"code": "invalid_price", "message": "Invalid price format."}},
                status=400,
            )

        # Parse amenities
        amenities = amenities_str.split(",") if amenities_str else None

        # Execute search
        hotels = HotelService.search_hotels(
            city=city,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            min_price=min_price,
            max_price=max_price,
            amenities=amenities,
        )

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(hotels, request)
        serializer = HotelSearchResultSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class HotelInfoView(APIView):
    """
    GET /api/hotels/{hotelId}/info

    Get full hotel details including rooms (public endpoint).
    Only returns active hotels.
    """

    permission_classes = [AllowAny]

    def get(self, request, hotel_id):
        try:
            hotel = Hotel.objects.select_related("contact_info").prefetch_related(
                "rooms"
            ).get(id=hotel_id, active=True)
        except Hotel.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Hotel not found or not active."}},
                status=404,
            )

        serializer = HotelDetailSerializer(hotel)
        return Response(serializer.data)
