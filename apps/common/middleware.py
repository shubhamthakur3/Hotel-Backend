"""
Custom middleware for the Hotel Backend API.
"""

import logging
import time
import uuid

logger = logging.getLogger("apps")


class RequestLoggingMiddleware:
    """
    Middleware that logs incoming requests and outgoing responses
    with timing information and a unique request ID.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate a unique request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id

        # Log the incoming request
        start_time = time.time()
        logger.info(
            "[%s] %s %s (User: %s)",
            request_id,
            request.method,
            request.get_full_path(),
            getattr(request.user, "email", "anonymous"),
        )

        # Process the request
        response = self.get_response(request)

        # Calculate response time
        duration_ms = (time.time() - start_time) * 1000

        # Log the response
        logger.info(
            "[%s] Response %d (%.2fms)",
            request_id,
            response.status_code,
            duration_ms,
        )

        # Add request ID to response headers for client-side debugging
        response["X-Request-ID"] = request_id
        response["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response
