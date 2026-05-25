from django.contrib import admin
from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_id", "username", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("user__email", "username", "telegram_id")
    readonly_fields = ("connect_token", "created_at", "updated_at")
    raw_id_fields = ("user",)
