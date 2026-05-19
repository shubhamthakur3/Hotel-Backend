from django.contrib import admin

from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("hotel", "type", "base_price", "total_count", "capacity")
    list_filter = ("type",)
    raw_id_fields = ("hotel",)
