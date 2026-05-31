"""URL configuration for admin booking-level endpoints."""

from django.urls import path

from .views import ManualConfirmBookingView

app_name = "adminpanel_bookings"

urlpatterns = [
    path("<int:booking_id>/manual-confirm/", ManualConfirmBookingView.as_view(), name="manual-confirm"),
]
