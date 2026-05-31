from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm, UserCreationForm as BaseUserCreationForm

from .models import User, UserRole


class UserChangeForm(BaseUserChangeForm):
    roles_list = forms.MultipleChoiceField(
        choices=UserRole.CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Roles",
        help_text="Select one or more roles for this user."
    )

    class Meta(BaseUserChangeForm.Meta):
        model = User

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['roles_list'].initial = self.instance.roles or []

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.roles = self.cleaned_data.get('roles_list', [])
        if commit:
            instance.save()
        return instance


class UserCreationForm(BaseUserCreationForm):
    roles_list = forms.MultipleChoiceField(
        choices=UserRole.CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Roles",
        help_text="Select one or more roles for this user."
    )

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email", "name")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.roles = self.cleaned_data.get('roles_list', [])
        if commit:
            instance.save()
        return instance


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for the User model."""

    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ("email", "name", "roles", "is_active", "date_joined")
    list_filter = ("is_active", "is_staff")
    search_fields = ("email", "name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("name", "roles_list")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2", "roles_list"),
            },
        ),
    )

