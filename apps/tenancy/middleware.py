from .models import Membership
from .services import create_workspace, get_active_workspace_for_user


class WorkspaceContextMiddleware:
    """Resolve the active workspace from session and attach it to the request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.workspace = None
        request.membership = None

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self.get_response(request)

        workspace, membership = get_active_workspace_for_user(request)
        if workspace is None:
            memberships = (
                Membership.objects.filter(user=request.user, is_active=True, workspace__is_active=True)
                .select_related("workspace")
                .order_by("workspace__name")
            )
            membership = memberships.first()
            if membership is not None:
                workspace = membership.workspace
            else:
                workspace = create_workspace(request.user, f"{request.user.first_name or request.user.email.split('@')[0]} Workspace")
                membership = Membership.objects.filter(user=request.user, workspace=workspace, is_active=True).first()

            if hasattr(request, 'session') and request.session is not None:
                request.session["active_workspace_id"] = str(workspace.id)
                request.session.modified = True

        if workspace is not None and membership is not None:
            request.workspace = workspace
            request.membership = membership

        return self.get_response(request)
