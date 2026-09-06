from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Read-only admin view for AuditLog records.
    Records are immutable by design — the model blocks save() and delete().
    We expose list/search/filter but hide the change/add/delete buttons.
    """

    list_display = ("created_at", "action", "user", "workspace", "ip_address", "path")
    list_filter = ("action", "workspace")
    search_fields = ("user__email", "workspace__slug", "path", "ip_address")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("user", "workspace", "action", "ip_address", "path", "payload", "created_at")

    # Prevent add/change/delete from the admin UI — logs are immutable
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
