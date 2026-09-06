"""
Comprehensive tenant isolation test suite — Part 1.

Covers:
  - IDOR prevention (User A cannot reach Workspace B data via API)
  - Role hierarchy correctness
  - Invitation lifecycle (create, accept, expiry, wrong-email guard)
  - WorkspaceScopedQuerySet.for_workspace(None) returns empty queryset
  - IsWorkspaceMember permission class behaviour
  - AuditLog carries workspace context
  - Middleware auto-creates default workspace for a brand-new user
  - switch_workspace() rejects non-members
"""
from datetime import timedelta

from django.test import TestCase, RequestFactory
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.core.models import Project
from apps.tenancy.models import Invitation, Membership, Workspace
from apps.tenancy.permissions import HasMinRole, IsWorkspaceMember
from apps.tenancy.querysets import WorkspaceScopedQuerySet
from apps.tenancy.services import (
    AlreadyMemberError,
    InvitationError,
    NotMemberError,
    accept_invitation,
    add_member,
    create_invitation,
    create_workspace,
    switch_workspace,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email, **kw):
    return CustomUser.objects.create_user(email=email, password="StrongPass!1", **kw)


def _fake_request(user, workspace=None, membership=None):
    """Build a minimal fake request object for permission tests."""
    req = RequestFactory().get("/")
    req.user = user
    req.workspace = workspace
    req.membership = membership
    return req


# ---------------------------------------------------------------------------
# 1. Tenant Isolation / IDOR
# ---------------------------------------------------------------------------

class TenantIsolationAPITest(TestCase):
    """User A must not be able to read or switch to Workspace B data."""

    def setUp(self):
        self.alice = _make_user("alice@example.com")
        self.bob = _make_user("bob@example.com")
        self.ws_alice = create_workspace(self.alice, "Alice WS")
        self.ws_bob = create_workspace(self.bob, "Bob WS")

        Project.objects.create(name="Alice Project", user=self.alice, workspace=self.ws_alice)
        Project.objects.create(name="Bob Project", user=self.bob, workspace=self.ws_bob)

    # --- API: list projects is workspace-scoped ---

    def test_alice_sees_only_her_projects_via_api(self):
        self.client.force_login(self.alice)
        self.client.session["active_workspace_id"] = str(self.ws_alice.id)
        session = self.client.session
        session["active_workspace_id"] = str(self.ws_alice.id)
        session.save()

        resp = self.client.get("/api/projects/")
        self.assertEqual(resp.status_code, 200)
        names = {r["name"] for r in resp.json()["results"]}
        self.assertIn("Alice Project", names)
        self.assertNotIn("Bob Project", names)

    # --- API: Bob cannot switch to Alice's workspace ---

    def test_bob_cannot_switch_to_alices_workspace_via_api(self):
        self.client.force_login(self.bob)
        resp = self.client.post(f"/api/v1/workspaces/{self.ws_alice.id}/switch/")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("not a member", resp.json()["error"].lower())

    # --- API: workspace list only returns workspaces user is a member of ---

    def test_workspace_list_returns_only_members_workspaces(self):
        self.client.force_login(self.alice)
        resp = self.client.get("/api/v1/workspaces/")
        self.assertEqual(resp.status_code, 200)
        ids = {ws["id"] for ws in resp.json()}
        self.assertIn(str(self.ws_alice.id), ids)
        self.assertNotIn(str(self.ws_bob.id), ids)

    # --- Service layer: switch_workspace raises for non-member ---

    def test_service_switch_workspace_rejects_non_member(self):
        req = type("R", (), {"user": self.bob, "session": {}})()
        with self.assertRaises(NotMemberError):
            switch_workspace(req, str(self.ws_alice.id))

    # --- Queryset: for_workspace(None) is always empty ---

    def test_for_workspace_none_returns_empty(self):
        qs = Project.objects.for_workspace(None)
        self.assertEqual(qs.count(), 0)
        self.assertIsInstance(qs, WorkspaceScopedQuerySet)

    # --- Queryset: for_workspace scopes correctly ---

    def test_for_workspace_scopes_to_correct_workspace(self):
        alice_qs = Project.objects.for_workspace(self.ws_alice)
        bob_qs = Project.objects.for_workspace(self.ws_bob)

        self.assertEqual(alice_qs.count(), 1)
        self.assertEqual(alice_qs.first().name, "Alice Project")

        self.assertEqual(bob_qs.count(), 1)
        self.assertEqual(bob_qs.first().name, "Bob Project")


# ---------------------------------------------------------------------------
# 2. Role Hierarchy
# ---------------------------------------------------------------------------

class RoleHierarchyTest(TestCase):

    def setUp(self):
        self.owner = _make_user("owner@example.com")
        self.ws = create_workspace(self.owner, "Role WS")
        self.admin = _make_user("admin@example.com")
        self.manager = _make_user("manager@example.com")
        self.member = _make_user("member@example.com")
        self.viewer = _make_user("viewer@example.com")

        add_member(self.ws, self.admin, Membership.Role.ADMIN)
        add_member(self.ws, self.manager, Membership.Role.MANAGER)
        add_member(self.ws, self.member, Membership.Role.MEMBER)
        add_member(self.ws, self.viewer, Membership.Role.VIEWER)

    def _get_membership(self, user):
        return Membership.objects.get(workspace=self.ws, user=user)

    def test_owner_has_all_roles(self):
        m = self._get_membership(self.owner)
        for role in Membership.Role:
            self.assertTrue(m.has_min_role(role), f"OWNER should satisfy {role}")

    def test_viewer_fails_member_and_above(self):
        m = self._get_membership(self.viewer)
        self.assertTrue(m.has_min_role(Membership.Role.VIEWER))
        self.assertFalse(m.has_min_role(Membership.Role.MEMBER))
        self.assertFalse(m.has_min_role(Membership.Role.MANAGER))
        self.assertFalse(m.has_min_role(Membership.Role.ADMIN))
        self.assertFalse(m.has_min_role(Membership.Role.OWNER))

    def test_manager_satisfies_member_and_viewer_but_not_admin(self):
        m = self._get_membership(self.manager)
        self.assertTrue(m.has_min_role(Membership.Role.VIEWER))
        self.assertTrue(m.has_min_role(Membership.Role.MEMBER))
        self.assertTrue(m.has_min_role(Membership.Role.MANAGER))
        self.assertFalse(m.has_min_role(Membership.Role.ADMIN))

    def test_admin_satisfies_up_to_admin_but_not_owner(self):
        m = self._get_membership(self.admin)
        self.assertTrue(m.has_min_role(Membership.Role.ADMIN))
        self.assertFalse(m.has_min_role(Membership.Role.OWNER))


# ---------------------------------------------------------------------------
# 3. Invitation Lifecycle
# ---------------------------------------------------------------------------

class InvitationLifecycleTest(TestCase):

    def setUp(self):
        self.owner = _make_user("owner@inv.com")
        self.ws = create_workspace(self.owner, "Inv WS")
        self.invitee = _make_user("invitee@inv.com")

    def test_create_invitation_generates_valid_token(self):
        inv = create_invitation(self.ws, "invitee@inv.com", Membership.Role.MEMBER)
        self.assertIsNotNone(inv.token)
        self.assertTrue(inv.is_valid)
        self.assertFalse(inv.is_accepted)

    def test_accept_invitation_creates_membership(self):
        inv = create_invitation(self.ws, "invitee@inv.com", Membership.Role.MEMBER)
        membership = accept_invitation(str(inv.token), self.invitee)
        self.assertEqual(membership.workspace, self.ws)
        self.assertEqual(membership.user, self.invitee)
        self.assertEqual(membership.role, Membership.Role.MEMBER)
        self.assertTrue(membership.is_active)

        inv.refresh_from_db()
        self.assertIsNotNone(inv.accepted_at)
        self.assertTrue(inv.is_accepted)

    def test_expired_invitation_is_rejected(self):
        inv = create_invitation(self.ws, "invitee@inv.com", Membership.Role.MEMBER)
        # Force expiry in the past
        inv.expires_at = timezone.now() - timedelta(hours=1)
        inv.save(update_fields=["expires_at"])

        with self.assertRaises(InvitationError):
            accept_invitation(str(inv.token), self.invitee)

    def test_already_accepted_invitation_is_rejected(self):
        inv = create_invitation(self.ws, "invitee@inv.com", Membership.Role.MEMBER)
        accept_invitation(str(inv.token), self.invitee)
        # Second accept must fail
        with self.assertRaises(InvitationError):
            accept_invitation(str(inv.token), self.invitee)

    def test_wrong_email_cannot_accept_invitation(self):
        inv = create_invitation(self.ws, "invitee@inv.com", Membership.Role.MEMBER)
        other = _make_user("other@example.com")
        with self.assertRaises(InvitationError):
            accept_invitation(str(inv.token), other)

    def test_invalid_token_raises_invitation_error(self):
        with self.assertRaises(InvitationError):
            accept_invitation("00000000-0000-0000-0000-000000000000", self.invitee)

    def test_add_member_raises_if_already_active(self):
        add_member(self.ws, self.invitee, Membership.Role.MEMBER)
        with self.assertRaises(AlreadyMemberError):
            add_member(self.ws, self.invitee, Membership.Role.ADMIN)

    def test_deactivated_member_can_be_readded(self):
        m = add_member(self.ws, self.invitee, Membership.Role.MEMBER)
        m.is_active = False
        m.save()
        # Re-add should succeed (re-activate)
        m2 = add_member(self.ws, self.invitee, Membership.Role.ADMIN)
        self.assertTrue(m2.is_active)
        self.assertEqual(m2.role, Membership.Role.ADMIN)


# ---------------------------------------------------------------------------
# 4. IsWorkspaceMember Permission Class
# ---------------------------------------------------------------------------

class IsWorkspaceMemberPermissionTest(TestCase):

    def setUp(self):
        self.user = _make_user("perm@example.com")
        self.ws = create_workspace(self.user, "Perm WS")
        self.membership = Membership.objects.get(workspace=self.ws, user=self.user)

    def test_grants_access_when_workspace_and_membership_present(self):
        req = _fake_request(self.user, workspace=self.ws, membership=self.membership)
        perm = IsWorkspaceMember()
        self.assertTrue(perm.has_permission(req, None))

    def test_denies_when_workspace_is_none(self):
        req = _fake_request(self.user, workspace=None, membership=self.membership)
        perm = IsWorkspaceMember()
        self.assertFalse(perm.has_permission(req, None))

    def test_denies_when_membership_is_none(self):
        req = _fake_request(self.user, workspace=self.ws, membership=None)
        perm = IsWorkspaceMember()
        self.assertFalse(perm.has_permission(req, None))

    def test_denies_when_membership_is_inactive(self):
        self.membership.is_active = False
        self.membership.save()
        req = _fake_request(self.user, workspace=self.ws, membership=self.membership)
        perm = IsWorkspaceMember()
        self.assertFalse(perm.has_permission(req, None))

    def test_has_min_role_permission_grants_correct_role(self):
        AdminPerm = HasMinRole(Membership.Role.ADMIN)
        req = _fake_request(self.user, workspace=self.ws, membership=self.membership)
        # OWNER satisfies ADMIN
        self.assertTrue(AdminPerm().has_permission(req, None))

    def test_has_min_role_denies_insufficient_role(self):
        viewer = _make_user("viewer2@example.com")
        v_membership = add_member(self.ws, viewer, Membership.Role.VIEWER)
        AdminPerm = HasMinRole(Membership.Role.ADMIN)
        req = _fake_request(viewer, workspace=self.ws, membership=v_membership)
        self.assertFalse(AdminPerm().has_permission(req, None))


# ---------------------------------------------------------------------------
# 5. Audit Log Carries Workspace Context
# ---------------------------------------------------------------------------

class AuditLogWorkspaceContextTest(TestCase):

    def setUp(self):
        self.user = _make_user("audit@example.com")
        self.ws = create_workspace(self.user, "Audit WS")

    def test_audit_log_records_workspace_on_api_request(self):
        from apps.audit.models import AuditLog

        self.client.force_login(self.user)
        session = self.client.session
        session["active_workspace_id"] = str(self.ws.id)
        session.save()

        self.client.get("/api/v1/workspaces/current/")

        log = AuditLog.objects.filter(user=self.user, workspace=self.ws).first()
        self.assertIsNotNone(log, "AuditLog should have workspace context set")
        self.assertEqual(log.workspace, self.ws)


# ---------------------------------------------------------------------------
# 6. Middleware Auto-Creates Default Workspace for New Users
# ---------------------------------------------------------------------------

class MiddlewareAutoWorkspaceTest(TestCase):

    def test_new_user_gets_workspace_on_first_request(self):
        new_user = _make_user("brand_new@example.com")
        # Confirm no workspace yet (create_user doesn't auto-create one)
        self.assertEqual(
            Membership.objects.filter(user=new_user, is_active=True).count(), 0
        )

        self.client.force_login(new_user)
        # Hit any authenticated endpoint — middleware should auto-create workspace
        resp = self.client.get("/api/v1/workspaces/current/")
        self.assertEqual(resp.status_code, 200)

        # Now a workspace must exist for this user
        self.assertTrue(
            Membership.objects.filter(user=new_user, is_active=True).exists(),
            "Middleware should have auto-created a default workspace",
        )
        workspace = Membership.objects.get(user=new_user, is_active=True).workspace
        self.assertEqual(workspace.owner, new_user)
        self.assertTrue(workspace.is_active)
