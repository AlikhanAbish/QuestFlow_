from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Company, Invitation, Team


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "max_users", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "owner__email")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("name", "slug", "owner", "is_active", "max_users"),
        }),
        (_("Feature flags"), {
            "fields": ("settings",),
            "classes": ("collapse",),
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "manager", "created_at")
    list_filter = ("company",)
    search_fields = ("name", "company__name", "manager__email")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "email", "company", "role", "is_accepted", "expires_at", "invited_by", "created_at"
    )
    list_filter = ("is_accepted", "role", "company")
    search_fields = ("email", "company__name", "invited_by__email")
    readonly_fields = ("token", "created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
