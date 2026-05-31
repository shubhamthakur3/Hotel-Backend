"""URL configuration for payment/webhook endpoints."""

from django.urls import path

from .views import StripeWebhookView

app_name = "payments"

urlpatterns = [
    path("payment/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
