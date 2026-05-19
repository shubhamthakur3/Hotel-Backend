"""
Custom throttle classes for rate limiting.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """
    Strict rate limiting for authentication endpoints.
    Prevents brute-force login attempts.
    """

    rate = "5/minute"
    scope = "auth"


class BurstRateThrottle(UserRateThrottle):
    """
    Burst rate limiting for general API endpoints.
    """

    rate = "60/minute"
    scope = "burst"


class BookingRateThrottle(UserRateThrottle):
    """
    Rate limiting for booking creation to prevent abuse.
    """

    rate = "10/minute"
    scope = "booking"
