"""
Payment views — Stripe webhook handler.

The webhook endpoint is the source of truth for payment confirmation.
It must return 200 quickly to avoid Stripe retries.
"""

import logging

from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import WebhookService

logger = logging.getLogger(__name__)


class StripeWebhookView(APIView):
    """
    POST /api/webhook/payment

    Stripe webhook handler. Receives events from Stripe
    and processes payment confirmations/failures.

    IMPORTANT:
    - This endpoint is exempt from CSRF and JWT authentication.
    - Security is enforced via Stripe signature verification.
    - Must return 200 quickly — heavy processing is offloaded to Celery.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # No JWT auth for webhooks

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        # Verify the webhook signature
        try:
            event = WebhookService.verify_webhook_signature(payload, sig_header)
        except Exception as e:
            logger.warning("Webhook signature verification failed: %s", str(e))
            return Response(
                {"error": "Invalid signature"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Route the event to the appropriate handler
        event_type = event.get("type", "")
        session = event.get("data", {}).get("object", {})

        logger.info("Received Stripe webhook: %s", event_type)

        try:
            if event_type == "checkout.session.completed":
                WebhookService.handle_checkout_completed(session)

            elif event_type == "checkout.session.expired":
                WebhookService.handle_checkout_expired(session)

            elif event_type in ("payment_intent.payment_failed",):
                WebhookService.handle_payment_failed(session)

            else:
                logger.info("Unhandled webhook event type: %s", event_type)

        except Exception as e:
            # Log but still return 200 to prevent Stripe retries
            logger.error(
                "Error processing webhook event %s: %s",
                event_type, str(e),
                exc_info=True,
            )

        # Always return 200 to acknowledge receipt
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
