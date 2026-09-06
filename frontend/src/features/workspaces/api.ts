import { apiClient } from '../../api/client';
import type { Workspace, WorkspaceCurrentResponse } from '../../types';

export const getWorkspacesFn = async (): Promise<Workspace[]> => {
  const { data } = await apiClient.get<Workspace[]>('/api/v1/workspaces/');
  return data;
};

export const getCurrentWorkspaceFn = async (): Promise<WorkspaceCurrentResponse> => {
  const { data } = await apiClient.get<WorkspaceCurrentResponse>('/api/v1/workspaces/current/');
  return data;
};

export const switchWorkspaceFn = async (workspaceId: string): Promise<WorkspaceCurrentResponse> => {
  const { data } = await apiClient.post<WorkspaceCurrentResponse>(`/api/v1/workspaces/${workspaceId}/switch/`);
  return data;
};

export const createWorkspaceFn = async (name: string): Promise<{ workspace: Workspace; message: string }> => {
  const { data } = await apiClient.post<{ workspace: Workspace; message: string }>('/api/v1/workspaces/', { name });
  return data;
};
