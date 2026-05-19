from django.contrib import admin

from .models import PricingRule


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "rule_type", "multiplier", "start_date", "end_date", "is_active")
    list_filter = ("rule_type", "is_active")
    search_fields = ("name",)
