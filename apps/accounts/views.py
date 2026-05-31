"""
Authentication views: signup, login, token refresh.

Login stores the refresh token in an HttpOnly cookie and returns
the access token in the response body for XSS protection.
"""

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.common.throttles import AuthRateThrottle

from .serializers import LoginSerializer, SignupSerializer

logger = logging.getLogger(__name__)

# Cookie settings
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


class SignupView(APIView):
    """
    POST /api/auth/signup

    Register a new user with the GUEST role.
    Returns access token in body and refresh token in HttpOnly cookie.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        logger.info("New user registered: %s", user.email)

        response = Response(
            {
                "message": "Registration successful.",
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "roles": user.roles,
                },
                "access_token": access_token,
            },
            status=status.HTTP_201_CREATED,
        )

        # Set refresh token in HttpOnly cookie
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=str(refresh),
            max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            path="/api/auth/",
        )

        return response


class LoginView(APIView):
    """
    POST /api/auth/login

    Authenticate user with email/password.
    Returns access token in body and refresh token in HttpOnly cookie.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        logger.info("User logged in: %s", user.email)

        response = Response(
            {
                "message": "Login successful.",
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "roles": user.roles,
                },
                "access_token": access_token,
            },
            status=status.HTTP_200_OK,
        )

        # Set refresh token in HttpOnly cookie
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=str(refresh),
            max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            path="/api/auth/",
        )

        return response


class TokenRefreshView(APIView):
    """
    POST /api/auth/refresh

    Reads refresh token from HttpOnly cookie, rotates it,
    and returns a new access token.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE_NAME)

        if not refresh_token:
            return Response(
                {"error": {"code": "no_refresh_token", "message": "No refresh token provided."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        from apps.accounts.models import User

        try:
            refresh = RefreshToken(refresh_token)

            # Get the user object for proper rotation
            user_id = refresh.payload.get("user_id")
            user = User.objects.get(id=user_id)
            
            # Blacklist the old refresh token
            refresh.blacklist()
            
            # Generate new tokens
            new_refresh = RefreshToken.for_user(user)
            access_token = str(new_refresh.access_token)

            response = Response(
                {
                    "message": "Token refreshed successfully.",
                    "access_token": access_token,
                },
                status=status.HTTP_200_OK,
            )

            # Set new refresh token in cookie
            response.set_cookie(
                key=REFRESH_TOKEN_COOKIE_NAME,
                value=str(new_refresh),
                max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
                path="/api/auth/",
            )

            return response

        except TokenError as e:
            logger.warning("Token refresh failed: %s", str(e))
            return Response(
                {"error": {"code": "invalid_token", "message": "Invalid or expired refresh token."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "user_not_found", "message": "User not found."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    """
    POST /api/auth/logout

    Blacklists the current refresh token and clears the cookie.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE_NAME)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass  # Token already blacklisted or invalid, that's fine

        response = Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )
        response.delete_cookie(
            REFRESH_TOKEN_COOKIE_NAME,
            path="/api/auth/",
        )
        return response
