# Multi-Tenancy Foundation (Part 1)

## Architecture

- `apps.tenancy` owns tenant primitives: `Workspace`, `Membership`, `Invitation`, and `WorkspaceSettings`.
- Every tenant-scoped resource should include a `workspace` FK and be queried through the active workspace context.
- The active workspace is resolved from the session (`active_workspace_id`) and verified against the current user’s active memberships.
- Workspace membership is strict: a user must be a member of the target workspace before the app resolves that workspace on the request.

## Resolution flow

1. Authentication middleware populates `request.user`.
2. `WorkspaceContextMiddleware` reads `request.session['active_workspace_id']`.
3. `get_active_workspace_for_user()` validates that the workspace exists, is active, and the user is an active member.
4. If the session is invalid or unset, the middleware falls back to the user’s first active workspace and stores it in the session.
5. Requests receive `request.workspace` and `request.membership` for downstream tenant checks.

## Isolation rules

- `Project.objects.for_workspace(request.workspace)` is the default tenant-aware query path.
- API endpoints never accept a workspace id without re-checking membership.
- Cross-workspace access is blocked by both view logic and the middleware guard.
- Audit records can carry `workspace` context for traceability without mutating immutable logs after creation.

## Migration strategy

The Part 1 migration is intentionally safe:

- Add `Project.workspace` as nullable during the migration.
- Create a default workspace per user and assign existing projects to that workspace.
- Reconcile memberships and settings for each workspace.
- Convert the field to non-null after data backfill.

This preserves existing project data and avoids destructive data loss while introducing tenant ownership.

## Security validations

- `switch_workspace()` verifies workspace existence and membership before writing the session.
- `WorkspaceViewSet.current` and `WorkspaceViewSet.switch` require membership checks before returning data.
- The middleware clears stale `active_workspace_id` values when the user loses access to the workspace.
- The API guards IDOR attempts by ensuring `request.user` is always validated as a workspace member before resolving the request context.

## Future Part 2

- Move Stripe billing and entitlement data to workspace-level ownership.
- Add invitation emails and automatic provisioning flows.
- Expand RBAC to full role policies beyond the Part 1 membership model.
- Add workspace admin dashboards, white-label configuration, and resource-level access rules.
