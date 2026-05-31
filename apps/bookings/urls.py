"""URL configuration for booking endpoints."""

from django.urls import path

from .views import (
    BookingAddGuestsView,
    BookingCancelView,
    BookingInitView,
    BookingPaymentView,
    BookingStatusView,
)

app_name = "bookings"

urlpatterns = [
    path("init/", BookingInitView.as_view(), name="booking-init"),
    path("<int:booking_id>/addGuests/", BookingAddGuestsView.as_view(), name="booking-add-guests"),
    path("<int:booking_id>/payments/", BookingPaymentView.as_view(), name="booking-payment"),
    path("<int:booking_id>/cancel/", BookingCancelView.as_view(), name="booking-cancel"),
    path("<int:booking_id>/status/", BookingStatusView.as_view(), name="booking-status"),
]
