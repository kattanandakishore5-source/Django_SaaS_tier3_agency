from django.contrib import admin

from .models import Invitation, Membership, Workspace, WorkspaceSettings


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "is_active", "created_at")
    search_fields = ("name", "slug", "owner__email")
    list_filter = ("is_active",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("workspace", "user", "role", "is_active")
    search_fields = ("workspace__slug", "user__email")
    list_filter = ("role", "is_active")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("workspace", "email", "role", "expires_at", "accepted_at")
    list_filter = ("role", "accepted_at")
    search_fields = ("email", "workspace__slug")


@admin.register(WorkspaceSettings)
class WorkspaceSettingsAdmin(admin.ModelAdmin):
    list_display = ("workspace", "timezone", "locale")
    search_fields = ("workspace__slug",)
