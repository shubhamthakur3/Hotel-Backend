"""URL configuration for user profile and guest endpoints."""

from django.urls import path

from .views import GuestDetailView, GuestListCreateView, MyBookingsView, UserProfileView

app_name = "users"

urlpatterns = [
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("myBookings/", MyBookingsView.as_view(), name="my-bookings"),
    path("guests/", GuestListCreateView.as_view(), name="guest-list-create"),
    path("guests/<int:guest_id>/", GuestDetailView.as_view(), name="guest-detail"),
]
