from django.contrib import admin

from .models import Guest


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "gender", "created_at")
    search_fields = ("name", "user__email")
    raw_id_fields = ("user",)
