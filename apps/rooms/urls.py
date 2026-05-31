"""URL configuration for room admin endpoints."""

from django.urls import path

from .views import RoomDetailView, RoomListCreateView

app_name = "rooms"

urlpatterns = [
    path("<int:hotel_id>/rooms/", RoomListCreateView.as_view(), name="room-list-create"),
    path("<int:hotel_id>/rooms/<int:room_id>/", RoomDetailView.as_view(), name="room-detail"),
]
