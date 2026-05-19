from django.contrib import admin

from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("room", "date", "booked_count", "total_count", "surge_factor", "closed")
    list_filter = ("closed", "date")
    raw_id_fields = ("hotel", "room")
    date_hierarchy = "date"
