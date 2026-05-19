"""
Custom exception classes and DRF exception handler for the Hotel Backend API.

Provides structured, consistent error responses across all endpoints.
"""

import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# ─── Custom Exception Classes ──────────────────────────────────────────────────


class ResourceNotFoundException(APIException):
    """Raised when a requested resource is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "not_found"


class ResourceConflictException(APIException):
    """Raised when an operation conflicts with the current state (e.g., double booking)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested operation conflicts with the current resource state."
    default_code = "conflict"


class BadRequestException(APIException):
    """Raised for invalid client requests."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request was invalid."
    default_code = "bad_request"


class UnauthorizedException(APIException):
    """Raised when authentication fails or is missing."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication credentials were not provided or are invalid."
    default_code = "unauthorized"


class ForbiddenException(APIException):
    """Raised when user does not have permission."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "forbidden"


class PaymentException(APIException):
    """Raised when a payment-related error occurs."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Payment processing failed."
    default_code = "payment_error"


class BookingException(APIException):
    """Raised for booking lifecycle errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Booking operation failed."
    default_code = "booking_error"


class InventoryException(APIException):
    """Raised when inventory is unavailable or cannot be modified."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Inventory is not available for the requested dates."
    default_code = "inventory_unavailable"


# ─── Custom Exception Handler ──────────────────────────────────────────────────


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that provides consistent error response format.

    Response format:
    {
        "error": {
            "code": "error_code",
            "message": "Human-readable message",
            "details": {...}  // optional
        }
    }
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exceptions — log and return 500
        logger.exception(
            "Unhandled exception in %s: %s",
            context.get("view", "unknown"),
            str(exc),
        )
        return Response(
            {
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred. Please try again later.",
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Structure the error response
    error_data = {
        "error": {
            "code": getattr(exc, "default_code", "error"),
            "message": str(exc.detail) if hasattr(exc, "detail") else str(exc),
        }
    }

    # For validation errors, include field-level details
    if isinstance(exc, ValidationError) and isinstance(exc.detail, dict):
        error_data["error"]["code"] = "validation_error"
        error_data["error"]["message"] = "Validation failed."
        error_data["error"]["details"] = exc.detail

    # For 404s, provide a cleaner message
    if isinstance(exc, Http404):
        error_data["error"]["code"] = "not_found"
        error_data["error"]["message"] = "The requested resource was not found."

    response.data = error_data

    # Log non-trivial errors
    if response.status_code >= 500:
        logger.error("Server error [%d]: %s", response.status_code, error_data)
    elif response.status_code >= 400:
        logger.warning("Client error [%d]: %s", response.status_code, error_data)

    return response
