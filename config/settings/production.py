"""
Production-specific Django settings.

Usage: DJANGO_SETTINGS_MODULE=config.settings.production
"""

from .base import *  # noqa: F401, F403

# ─── Debug ──────────────────────────────────────────────────────────────────────

DEBUG = False

# ─── Security ───────────────────────────────────────────────────────────────────

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ─── Email (SMTP) ──────────────────────────────────────────────────────────────

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")  # noqa: F405
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)  # noqa: F405
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)  # noqa: F405
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@hotelbooking.com")  # noqa: F405

# ─── Logging (production — file + console) ─────────────────────────────────────

LOGGING["loggers"]["apps"]["level"] = "WARNING"  # noqa: F405
