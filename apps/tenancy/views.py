from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Membership, Workspace
from .serializers import MembershipSerializer, WorkspaceSerializer
from .services import NotMemberError, WorkspaceError, create_workspace, get_or_create_default_workspace_for_user, switch_workspace


class WorkspaceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _workspace_queryset(self):
        return (
            Workspace.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
                is_active=True,
            )
            .distinct()
            .order_by("name")
        )

    def list(self, request):
        workspaces = self._workspace_queryset()
        if not workspaces.exists():
            workspaces = Workspace.objects.filter(pk=get_or_create_default_workspace_for_user(request.user).pk)
        serializer = WorkspaceSerializer(workspaces, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        workspace = getattr(request, "workspace", None)
        if workspace is None:
            workspace = get_or_create_default_workspace_for_user(request.user)
            request.workspace = workspace

        membership = Membership.objects.filter(
            user=request.user,
            workspace=workspace,
            is_active=True,
        ).select_related("workspace").first()
        if membership is None:
            return Response({"error": "You are not a member of this workspace."}, status=status.HTTP_403_FORBIDDEN)

        payload = {
            "workspace": WorkspaceSerializer(workspace, context={"request": request}).data,
            "role": membership.role,
            "membership_id": membership.id,
        }
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="switch")
    def switch(self, request, pk=None):
        try:
            workspace = switch_workspace(request, pk)
        except (WorkspaceError, NotMemberError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        # Re-fetch membership so we can return role + membership_id — same shape
        # as /current/ so the frontend WorkspaceContext can update without a
        # second round-trip.
        membership = Membership.objects.filter(
            workspace=workspace, user=request.user, is_active=True
        ).first()

        return Response({
            "workspace": WorkspaceSerializer(workspace, context={"request": request}).data,
            "role": membership.role if membership else None,
            "membership_id": membership.id if membership else None,
        })

    def create(self, request):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"error": "Workspace name is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                workspace = create_workspace(request.user, name)
        except WorkspaceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        request.session["active_workspace_id"] = str(workspace.id)
        request.session.modified = True
        return Response(
            {"message": "Workspace created successfully.", "workspace": WorkspaceSerializer(workspace, context={"request": request}).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="memberships")
    def memberships(self, request):
        memberships = Membership.objects.filter(user=request.user, is_active=True).select_related("workspace")
        serializer = MembershipSerializer(memberships, many=True)
        return Response(serializer.data)
