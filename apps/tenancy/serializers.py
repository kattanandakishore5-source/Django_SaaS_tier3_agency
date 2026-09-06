from rest_framework import serializers

from .models import Membership, Workspace, WorkspaceSettings


class WorkspaceSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "owner", "is_active", "role", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "owner", "is_active", "created_at", "updated_at"]

    def get_role(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request.user, "is_authenticated", False):
            return None
        membership = Membership.objects.filter(
            workspace=obj,
            user=request.user,
            is_active=True,
        ).first()
        return membership.role if membership else None


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    workspace_slug = serializers.CharField(source="workspace.slug", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "workspace",
            "workspace_slug",
            "user",
            "user_email",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "workspace", "user", "created_at", "updated_at"]


class WorkspaceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceSettings
        fields = ["workspace", "timezone", "locale", "updated_at"]
        read_only_fields = ["workspace", "updated_at"]
