"""Inventory admin views."""

import logging
from datetime import datetime

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrManager
from apps.common.pagination import StandardResultsPagination

from .models import Inventory
from .serializers import InventoryBulkUpdateSerializer, InventorySerializer
from .services import InventoryService

logger = logging.getLogger(__name__)


class RoomInventoryView(APIView):
    """
    GET   /api/admin/inventory/rooms/{roomId}  — View room inventory
    PATCH /api/admin/inventory/rooms/{roomId}  — Bulk update inventory
    """

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request, room_id):
        """Retrieve inventory for a room, with optional date range filters."""
        from apps.rooms.services import RoomService

        room = RoomService.get_room_or_404(room_id)

        # Parse optional date filters
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        inventory = InventoryService.get_room_inventory(room_id, start_date, end_date)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(inventory, request)
        serializer = InventorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def patch(self, request, room_id):
        """
        Bulk update inventory records (surge_factor, closed, total_count).

        Body:
        {
            "updates": [
                {"date": "2026-07-10", "surge_factor": 1.5},
                {"date": "2026-07-11", "closed": true}
            ]
        }
        """
        from apps.rooms.services import RoomService

        room = RoomService.get_room_or_404(room_id)

        serializer = InventoryBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = InventoryService.update_inventory_bulk(
            room_id=room_id,
            updates=serializer.validated_data["updates"],
        )

        return Response(
            {"message": f"Updated {updated} inventory records."},
            status=status.HTTP_200_OK,
        )
