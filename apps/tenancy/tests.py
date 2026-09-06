from django.test import TestCase

from apps.accounts.models import CustomUser
from apps.core.models import Project
from apps.tenancy.models import Membership, Workspace, WorkspaceSettings
from apps.tenancy.services import NotMemberError, create_workspace, switch_workspace


class WorkspaceFoundationTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email='owner@example.com', password='StrongPass!123')
        self.other_user = CustomUser.objects.create_user(email='member@example.com', password='StrongPass!123')
        self.outsider = CustomUser.objects.create_user(email='outsider@example.com', password='StrongPass!123')
        self.workspace = create_workspace(self.user, 'Alpha Studio')
        Membership.objects.create(workspace=self.workspace, user=self.other_user, role=Membership.Role.MEMBER, is_active=True)

        self.other_workspace = create_workspace(self.other_user, 'Beta Studio')
        Membership.objects.create(workspace=self.other_workspace, user=self.user, role=Membership.Role.ADMIN, is_active=True)

    def test_membership_uniqueness_and_workspace_creation(self):
        self.assertTrue(self.workspace.pk)
        self.assertEqual(self.workspace.memberships.filter(user=self.user, is_active=True).count(), 1)
        self.assertEqual(Membership.objects.filter(workspace=self.workspace, user=self.user).count(), 1)

    def test_create_workspace_atomically_creates_settings(self):
        """create_workspace must always produce a WorkspaceSettings companion."""
        self.assertTrue(WorkspaceSettings.objects.filter(workspace=self.workspace).exists())
        settings_obj = self.workspace.settings
        self.assertEqual(settings_obj.timezone, "UTC")
        self.assertEqual(settings_obj.locale, "en")

    def test_active_workspace_is_resolved_from_session(self):
        session = self.client.session
        session['active_workspace_id'] = str(self.workspace.id)
        session.save()
        self.client.force_login(self.user)

        response = self.client.get('/api/v1/workspaces/current/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['workspace']['name'], 'Alpha Studio')

    def test_switching_workspace_requires_membership(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/api/v1/workspaces/{self.other_workspace.id}/switch/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['workspace']['name'], self.other_workspace.name)

        self.client.force_login(self.outsider)
        response = self.client.post(f'/api/v1/workspaces/{self.workspace.id}/switch/')
        self.assertEqual(response.status_code, 403)
        self.assertIn('not a member', str(response.json()['error']).lower())

    def test_switch_response_includes_role_and_membership_id(self):
        """Switch endpoint must return role + membership_id (WorkspaceCurrentResponse shape)."""
        self.client.force_login(self.user)
        response = self.client.post(f'/api/v1/workspaces/{self.other_workspace.id}/switch/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('role', data)
        self.assertIn('membership_id', data)
        self.assertIn('workspace', data)
        self.assertEqual(data['role'], Membership.Role.ADMIN)

    def test_project_queries_are_workspace_scoped(self):
        first_workspace_project = Project.objects.create(
            name='Alpha project',
            user=self.user,
            workspace=self.workspace,
        )
        other_workspace_project = Project.objects.create(
            name='Beta project',
            user=self.other_user,
            workspace=self.other_workspace,
        )

        self.client.force_login(self.user)
        session = self.client.session
        session['active_workspace_id'] = str(self.workspace.id)
        session.save()

        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, 200)
        names = {row['name'] for row in response.json()['results']}
        self.assertIn(first_workspace_project.name, names)
        self.assertNotIn(other_workspace_project.name, names)

    def test_service_rejects_non_member_workspace_switch(self):
        request = type('Request', (), {'user': self.outsider, 'session': {}})()
        with self.assertRaises(NotMemberError):
            switch_workspace(request, str(self.workspace.id))
