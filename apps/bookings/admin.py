from django.contrib import admin

from .models import Booking, BookingGuest


class BookingGuestInline(admin.TabularInline):
    model = BookingGuest
    extra = 0
    raw_id_fields = ("guest",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "hotel", "room", "user", "status", "check_in_date", "checkout_date", "total_price")
    list_filter = ("status",)
    search_fields = ("user__email", "hotel__name")
    raw_id_fields = ("hotel", "room", "user", "payment")
    inlines = [BookingGuestInline]
    date_hierarchy = "created_at"
