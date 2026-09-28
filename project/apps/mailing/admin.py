from apps.mailing.models import Mailing
from django.contrib import admin


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    list_display = (
        "external_id",
        "user",
        "email",
        "subject",
        "status",
        "sent_at",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("external_id", "email", "subject")
