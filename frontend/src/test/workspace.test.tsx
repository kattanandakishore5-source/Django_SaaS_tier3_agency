import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { WorkspaceContext } from '../features/workspaces/WorkspaceContext';
import { WorkspaceSwitcher } from '../features/workspaces/WorkspaceSwitcher';

const workspace = {
  id: 'ws-1',
  name: 'Acme',
  slug: 'acme',
  owner: 1,
  is_active: true,
  role: 'OWNER',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('WorkspaceSwitcher', () => {
  it('renders the active workspace and lets a user create a new workspace', async () => {
    const switchWorkspace = vi.fn().mockResolvedValue(undefined);
    const createWorkspace = vi.fn().mockResolvedValue(undefined);

    render(
      <WorkspaceContext.Provider
        value={{
          workspaces: [workspace],
          currentWorkspace: workspace,
          currentRole: 'OWNER',
          isLoading: false,
          error: null,
          switchWorkspace,
          createWorkspace,
          refresh: vi.fn(),
        }}
      >
        <WorkspaceSwitcher />
      </WorkspaceContext.Provider>
    );

    expect(screen.getByText('Acme')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /Acme/i }));
    fireEvent.click(screen.getByRole('button', { name: /Create workspace/i }));
    fireEvent.change(screen.getByPlaceholderText(/new workspace name/i), { target: { value: 'Northwind' } });
    fireEvent.click(screen.getByRole('button', { name: /Create/i }));

    await waitFor(() => expect(createWorkspace).toHaveBeenCalledWith('Northwind'));
  });
});
