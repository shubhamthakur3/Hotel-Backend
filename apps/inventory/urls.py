"""URL configuration for inventory admin endpoints."""

from django.urls import path

from .views import RoomInventoryView

app_name = "inventory"

urlpatterns = [
    path("rooms/<int:room_id>/", RoomInventoryView.as_view(), name="room-inventory"),
]
