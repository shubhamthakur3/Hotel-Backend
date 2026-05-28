"""
Root URL Configuration for Hotel Backend API.

All API routes are namespaced under /api/.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # OpenAPI Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Django Admin
    path("admin/panel/", admin.site.urls),

    # ─── Authentication ─────────────────────────────────────────────────────
    path("api/auth/", include("apps.accounts.urls")),

    # ─── User Profile & Guests ──────────────────────────────────────────────
    path("api/users/", include("apps.users.urls")),

    # ─── Hotel Browse (Public) ──────────────────────────────────────────────
    path("api/hotels/", include("apps.hotels.urls_browse")),

    # ─── Hotel Admin Management ─────────────────────────────────────────────
    path("api/admin/hotels/", include("apps.hotels.urls_admin")),

    # ─── Room Admin Management ──────────────────────────────────────────────
    path("api/admin/hotels/", include("apps.rooms.urls")),

    # ─── Inventory Admin ────────────────────────────────────────────────────
    path("api/admin/inventory/", include("apps.inventory.urls")),

    # ─── Bookings ───────────────────────────────────────────────────────────
    path("api/bookings/", include("apps.bookings.urls")),

    # ─── Admin Panel (Reports & Bookings) ───────────────────────────────────
    path("api/admin/hotels/", include("apps.adminpanel.urls")),

    # ─── Admin Booking Management (Manual Confirm) ──────────────────────────
    path("api/admin/bookings/", include("apps.adminpanel.urls_bookings")),

    # ─── Webhook ────────────────────────────────────────────────────────────
    path("api/webhook/", include("apps.payments.urls")),
]
