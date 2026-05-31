"""URL configuration for hotel browse (public) endpoints."""

from django.urls import path

from .views_browse import HotelInfoView, HotelSearchView

app_name = "hotels_browse"

urlpatterns = [
    path("search/", HotelSearchView.as_view(), name="hotel-search"),
    path("<int:hotel_id>/info/", HotelInfoView.as_view(), name="hotel-info"),
]
