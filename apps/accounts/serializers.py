"""
Serializers for authentication endpoints.

Handles user registration, login, and token management.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, UserRole


class SignupSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Validates email uniqueness, password strength, and creates
    a new user with the GUEST role by default.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    roles = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = User
        fields = ["id", "name", "email", "password", "confirm_password", "roles"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        """Ensure email is unique (case-insensitive)."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        """Create user with hashed password and specified roles."""
        input_roles = validated_data.get("roles", [UserRole.GUEST])
        # Only allow GUEST and HOTEL_MANAGER via public signup
        allowed_roles = [UserRole.GUEST, UserRole.HOTEL_MANAGER]
        roles = [r for r in input_roles if r in allowed_roles]
        if not roles:
            roles = [UserRole.GUEST]

        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
            roles=roles,
        )


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.

    Validates credentials and returns user data.
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        email = attrs.get("email", "").lower()
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account has been deactivated."
            )

        attrs["user"] = user
        return attrs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes additional user claims.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims to the JWT payload
        token["name"] = user.name
        token["email"] = user.email
        token["roles"] = user.roles

        return token


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for viewing/updating user profile."""

    class Meta:
        model = User
        fields = ["id", "name", "email", "roles", "date_joined"]
        read_only_fields = ["id", "email", "roles", "date_joined"]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile (limited fields)."""

    class Meta:
        model = User
        fields = ["name"]
