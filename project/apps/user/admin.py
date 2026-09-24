from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name",)}),
        (_("Contact info"), {"fields": ("email",)}),
        (
            _("Permissions"),
            {"fields": ("is_active", "is_staff", "is_superuser", "role")},
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "email",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    list_display = (
        "first_name",
        "email",
    )

    readonly_fields = ("last_login", "date_joined")
