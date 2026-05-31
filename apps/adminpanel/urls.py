"""URL configuration for admin panel hotel-scoped endpoints."""

from django.urls import path

from .views import HotelBookingsListView, HotelReportView

app_name = "adminpanel"

urlpatterns = [
    path("<int:hotel_id>/bookings/", HotelBookingsListView.as_view(), name="hotel-bookings"),
    path("<int:hotel_id>/reports/", HotelReportView.as_view(), name="hotel-reports"),
]
