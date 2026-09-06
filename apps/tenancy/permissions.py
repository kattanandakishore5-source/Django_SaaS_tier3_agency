"""
Tenancy permission classes for DRF views.

Usage:
    class MyView(APIView):
        permission_classes = [IsAuthenticated, IsWorkspaceMember]

    # Or with minimum role:
    class AdminView(APIView):
        permission_classes = [IsAuthenticated, HasMinRole(Membership.Role.ADMIN)]
"""
from rest_framework.permissions import BasePermission

from .models import Membership


class IsWorkspaceMember(BasePermission):
    """
    Grants access only when:
      1. request.workspace is resolved (set by WorkspaceContextMiddleware)
      2. request.membership is active for request.user in that workspace

    Prevents accidental data leakage if the middleware is bypassed or workspace
    resolution fails (e.g., user has no workspaces yet during onboarding).
    """

    message = "You must be an active member of this workspace to access this resource."

    def has_permission(self, request, view):
        workspace = getattr(request, "workspace", None)
        membership = getattr(request, "membership", None)

        if workspace is None or membership is None:
            return False

        # Double-check the membership is still active (guard against stale middleware state)
        return (
            membership.is_active
            and membership.workspace_id == workspace.pk
            and membership.user_id == request.user.pk
        )


def HasMinRole(required_role: str):
    """
    Factory that returns a permission class enforcing a minimum role.

    Usage:
        permission_classes = [IsAuthenticated, HasMinRole(Membership.Role.ADMIN)]
    """

    class _HasMinRole(BasePermission):
        message = f"You need at least the '{required_role}' role to perform this action."

        def has_permission(self, request, view):
            membership = getattr(request, "membership", None)
            if membership is None or not membership.is_active:
                return False
            return membership.has_min_role(required_role)

    _HasMinRole.__name__ = f"HasMinRole_{required_role}"
    return _HasMinRole
