"""
Tenancy service layer — all mutations are transactional.
"""
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Invitation, Membership, Workspace, WorkspaceSettings


class WorkspaceError(Exception):
    """Base error for workspace service operations."""
    pass


class AlreadyMemberError(WorkspaceError):
    pass


class NotMemberError(WorkspaceError):
    pass


class InvitationError(WorkspaceError):
    pass


# ---------------------------------------------------------------------------
# Workspace creation
# ---------------------------------------------------------------------------

@transaction.atomic
def create_workspace(owner, name: str) -> Workspace:
    """
    Atomically create a Workspace + OWNER Membership + WorkspaceSettings.
    Returns the created Workspace instance.
    """
    cleaned_name = (name or "").strip()
    if not cleaned_name:
        raise WorkspaceError("Workspace name is required.")

    workspace = Workspace.objects.create(name=cleaned_name, owner=owner)
    Membership.objects.create(
        workspace=workspace,
        user=owner,
        role=Membership.Role.OWNER,
        is_active=True,
    )
    WorkspaceSettings.objects.create(workspace=workspace)
    return workspace


def get_or_create_default_workspace_for_user(user):
    """Return the user's default workspace or auto-create one when none exists."""
    membership = (
        Membership.objects.filter(user=user, is_active=True, workspace__is_active=True)
        .select_related("workspace")
        .order_by("workspace__name")
        .first()
    )
    if membership is not None:
        return membership.workspace

    base_name = getattr(user, 'first_name', '').strip() or (user.email.split('@')[0] if user.email else 'Workspace')
    return create_workspace(user, f"{base_name} Workspace")


# ---------------------------------------------------------------------------
# Membership management
# ---------------------------------------------------------------------------

@transaction.atomic
def add_member(workspace: Workspace, user, role: str, added_by=None) -> Membership:
    """
    Add a user to a workspace with the given role.
    Raises AlreadyMemberError if the user is already an active member.
    """
    existing = Membership.objects.filter(workspace=workspace, user=user).first()
    if existing:
        if existing.is_active:
            raise AlreadyMemberError(
                f"{user.email} is already a member of {workspace.slug}."
            )
        # Re-activate a previously deactivated membership
        existing.role = role
        existing.is_active = True
        existing.save(update_fields=["role", "is_active", "updated_at"])
        return existing

    return Membership.objects.create(
        workspace=workspace,
        user=user,
        role=role,
        is_active=True,
    )


@transaction.atomic
def remove_member(workspace: Workspace, user, removed_by=None) -> None:
    """
    Deactivate a user's membership. Owners cannot be removed.
    """
    membership = Membership.objects.filter(
        workspace=workspace, user=user, is_active=True
    ).first()
    if not membership:
        raise NotMemberError(f"{user.email} is not a member of {workspace.slug}.")
    if membership.role == Membership.Role.OWNER:
        raise WorkspaceError("The workspace owner cannot be removed.")
    membership.is_active = False
    membership.save(update_fields=["is_active", "updated_at"])


# ---------------------------------------------------------------------------
# Invitation management
# ---------------------------------------------------------------------------

INVITATION_EXPIRY_DAYS = 7


@transaction.atomic
def create_invitation(
    workspace: Workspace, email: str, role: str, invited_by=None
) -> Invitation:
    """
    Create a pending invitation for email to join workspace.
    Returns the Invitation instance (email sending deferred to Part 2).
    """
    expires_at = timezone.now() + timedelta(days=INVITATION_EXPIRY_DAYS)
    invitation = Invitation.objects.create(
        workspace=workspace,
        email=email,
        role=role,
        invited_by=invited_by,
        expires_at=expires_at,
    )
    return invitation


@transaction.atomic
def accept_invitation(token: str, user) -> Membership:
    """
    Accept an invitation by token. Validates expiry and creates membership.
    Returns the resulting Membership.
    """
    try:
        invitation = Invitation.objects.select_for_update().get(token=token)
    except Invitation.DoesNotExist:
        raise InvitationError("Invalid invitation token.")

    if not invitation.is_valid:
        raise InvitationError("This invitation has expired or has already been accepted.")

    if invitation.email.lower() != user.email.lower():
        raise InvitationError("This invitation was not issued for your email address.")

    membership = add_member(
        workspace=invitation.workspace,
        user=user,
        role=invitation.role,
    )
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    return membership


# ---------------------------------------------------------------------------
# Workspace context switching
# ---------------------------------------------------------------------------

def switch_workspace(request, workspace_id: str) -> Workspace:
    """
    Validate that request.user is an active member of workspace_id,
    then persist the choice in the session.
    Returns the Workspace on success, raises NotMemberError otherwise.
    """
    try:
        workspace = Workspace.objects.get(pk=workspace_id, is_active=True)
    except (Workspace.DoesNotExist, ValueError):
        raise WorkspaceError("Workspace not found.")

    is_member = Membership.objects.filter(
        workspace=workspace,
        user=request.user,
        is_active=True,
    ).exists()
    if not is_member:
        raise NotMemberError("You are not a member of this workspace.")

    if hasattr(request, 'session') and request.session is not None:
        request.session["active_workspace_id"] = str(workspace_id)
        request.session.modified = True
    return workspace


def get_active_workspace_for_user(request):
    """
    Resolve the active workspace from the session and verify membership.
    Returns (workspace, membership) or (None, None).
    """
    session = getattr(request, 'session', None)
    workspace_id = session.get('active_workspace_id') if session is not None else None
    if workspace_id:
        try:
            membership = Membership.objects.select_related("workspace").get(
                workspace_id=workspace_id,
                user=request.user,
                is_active=True,
                workspace__is_active=True,
            )
            return membership.workspace, membership
        except Membership.DoesNotExist:
            if session is not None:
                session.pop('active_workspace_id', None)
                session.modified = True
            return None, None

    return None, None
