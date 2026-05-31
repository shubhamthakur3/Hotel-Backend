"""URL configuration for hotel admin endpoints."""

from django.urls import path

from .views import HotelActivateView, HotelAdminDetailView, HotelAdminListCreateView

app_name = "hotels_admin"

urlpatterns = [
    path("", HotelAdminListCreateView.as_view(), name="hotel-list-create"),
    path("<int:hotel_id>/", HotelAdminDetailView.as_view(), name="hotel-detail"),
    path("<int:hotel_id>/activate/", HotelActivateView.as_view(), name="hotel-activate"),
]
