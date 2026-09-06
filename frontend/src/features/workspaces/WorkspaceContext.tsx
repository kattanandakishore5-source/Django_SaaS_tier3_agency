import React, { createContext, useCallback, useContext, useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../auth/AuthContext';
import { queryKeys } from '../../api/queryKeys';
import type { Workspace, WorkspaceCurrentResponse } from '../../types';
import {
  createWorkspaceFn,
  getCurrentWorkspaceFn,
  getWorkspacesFn,
  switchWorkspaceFn,
} from './api';

interface WorkspaceContextValue {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  currentRole: string | null;
  isLoading: boolean;
  error: Error | null;
  switchWorkspace: (workspaceId: string) => Promise<void>;
  createWorkspace: (name: string) => Promise<void>;
  refresh: () => Promise<void>;
}

export const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();

  const workspacesQuery = useQuery({
    queryKey: queryKeys.workspaces,
    queryFn: getWorkspacesFn,
    enabled: isAuthenticated,
    retry: false,
    // On 403/401 return empty array — don't crash the app
    throwOnError: false,
  });

  const currentWorkspaceQuery = useQuery({
    queryKey: queryKeys.currentWorkspace,
    queryFn: getCurrentWorkspaceFn,
    enabled: isAuthenticated,
    retry: false,
    throwOnError: false,
  });

  // Handle 403: if the user has lost access to the current workspace,
  // clear the cached current workspace and refetch the list so the
  // middleware can fall back to another workspace on the next request.
  const currentWorkspaceError = currentWorkspaceQuery.error as { status?: number } | null;
  const isForbidden = currentWorkspaceError?.status === 403 || currentWorkspaceError?.status === 401;

  const switchMutation = useMutation({
    mutationFn: switchWorkspaceFn,
    onSuccess: async (data: WorkspaceCurrentResponse) => {
      // Update current workspace cache immediately — same shape as /current/ response
      queryClient.setQueryData<WorkspaceCurrentResponse>(queryKeys.currentWorkspace, data);
      // Invalidate downstream queries that are workspace-scoped
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
      await queryClient.refetchQueries({ queryKey: queryKeys.workspaces });
    },
    onError: () => {
      // On switch failure, re-sync the current workspace from the server
      queryClient.invalidateQueries({ queryKey: queryKeys.currentWorkspace });
    },
  });

  const createMutation = useMutation({
    mutationFn: createWorkspaceFn,
    onSuccess: async (data) => {
      // Optimistically add the new workspace to the list
      queryClient.setQueryData<Workspace[]>(queryKeys.workspaces, (prev = []) => [
        ...prev.filter((ws) => ws.id !== data.workspace.id),
        data.workspace,
      ]);
      // New workspace becomes the active workspace (server already switched session)
      queryClient.setQueryData<WorkspaceCurrentResponse>(queryKeys.currentWorkspace, {
        workspace: data.workspace,
        role: 'OWNER',
        membership_id: null,
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
    onError: () => {
      // Re-sync on error
      queryClient.invalidateQueries({ queryKey: queryKeys.workspaces });
      queryClient.invalidateQueries({ queryKey: queryKeys.currentWorkspace });
    },
  });

  const refresh = useCallback(async () => {
    await Promise.all([
      queryClient.refetchQueries({ queryKey: queryKeys.workspaces }),
      queryClient.refetchQueries({ queryKey: queryKeys.currentWorkspace }),
    ]);
  }, [queryClient]);

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      workspaces: workspacesQuery.data ?? [],
      // If the current workspace returns 403, surface null so the UI
      // degrades gracefully instead of showing stale data.
      currentWorkspace: isForbidden ? null : (currentWorkspaceQuery.data?.workspace ?? null),
      currentRole: isForbidden ? null : (currentWorkspaceQuery.data?.role ?? null),
      isLoading: workspacesQuery.isLoading || currentWorkspaceQuery.isLoading,
      error: (workspacesQuery.error ?? currentWorkspaceQuery.error) as Error | null,
      switchWorkspace: async (workspaceId: string) => {
        await switchMutation.mutateAsync(workspaceId);
      },
      createWorkspace: async (name: string) => {
        await createMutation.mutateAsync(name);
      },
      refresh,
    }),
    [
      createMutation,
      currentWorkspaceQuery.data,
      currentWorkspaceQuery.error,
      currentWorkspaceQuery.isLoading,
      isForbidden,
      refresh,
      switchMutation,
      workspacesQuery.data,
      workspacesQuery.error,
      workspacesQuery.isLoading,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
};

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};
