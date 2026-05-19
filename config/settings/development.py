"""
Development-specific Django settings.

Usage: DJANGO_SETTINGS_MODULE=config.settings.development
"""

from .base import *  # noqa: F401, F403

# ─── Debug ──────────────────────────────────────────────────────────────────────

DEBUG = True

# ─── Email (Console) ───────────────────────────────────────────────────────────

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── CORS (allow all in dev) ───────────────────────────────────────────────────

CORS_ALLOW_ALL_ORIGINS = True

# ─── Additional DRF renderers for browsable API ───────────────────────────────

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# ─── Logging (more verbose in dev) ─────────────────────────────────────────────

LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405
