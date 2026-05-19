from django.contrib import admin

from .models import ContactInfo, Hotel, HotelMinPrice


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "active", "owner", "created_at")
    list_filter = ("active", "city")
    search_fields = ("name", "city")
    raw_id_fields = ("owner",)


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("email", "phone_number", "location")


@admin.register(HotelMinPrice)
class HotelMinPriceAdmin(admin.ModelAdmin):
    list_display = ("hotel", "date", "min_price")
    list_filter = ("date",)
    raw_id_fields = ("hotel",)
