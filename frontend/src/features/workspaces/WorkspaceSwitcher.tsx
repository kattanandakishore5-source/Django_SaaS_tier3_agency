import React, { useEffect, useRef, useMemo, useState } from 'react';
import { ChevronDown, Plus, Building2, Check, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { useWorkspace } from './WorkspaceContext';

export const WorkspaceSwitcher: React.FC = () => {
  const {
    workspaces,
    currentWorkspace,
    currentRole,
    switchWorkspace,
    createWorkspace,
    isLoading,
    error,
  } = useWorkspace();

  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [name, setName] = useState('');
  const [isSwitching, setIsSwitching] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setIsCreating(false);
        setLocalError(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  // Focus input when create form opens
  useEffect(() => {
    if (isCreating) inputRef.current?.focus();
  }, [isCreating]);

  const workspaceName = useMemo(
    () => currentWorkspace?.name ?? 'Select workspace',
    [currentWorkspace],
  );

  const handleSwitch = async (workspaceId: string) => {
    if (workspaceId === currentWorkspace?.id) {
      setIsOpen(false);
      return;
    }
    setIsSwitching(workspaceId);
    setLocalError(null);
    try {
      await switchWorkspace(workspaceId);
      setIsOpen(false);
    } catch {
      setLocalError('Failed to switch workspace. Please try again.');
    } finally {
      setIsSwitching(null);
    }
  };

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setIsSubmitting(true);
    setLocalError(null);
    try {
      await createWorkspace(trimmed);
      setName('');
      setIsCreating(false);
      setIsOpen(false);
    } catch {
      setLocalError('Failed to create workspace. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <Button variant="outline" size="sm" disabled className="gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Loading…</span>
      </Button>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        id="workspace-switcher-trigger"
        variant="outline"
        size="sm"
        className="gap-2 max-w-[220px]"
        onClick={() => {
          setIsOpen((open) => !open);
          setLocalError(null);
        }}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <Building2 className="h-4 w-4 shrink-0" />
        <span className="truncate">{workspaceName}</span>
        {currentRole && (
          <span className="hidden md:inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-muted text-muted-foreground shrink-0">
            {currentRole}
          </span>
        )}
        <ChevronDown className={`h-4 w-4 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </Button>

      {isOpen && (
        <div
          id="workspace-switcher-dropdown"
          className="absolute right-0 z-50 mt-2 w-72 rounded-lg border bg-popover shadow-lg p-2 space-y-1"
          role="listbox"
          aria-label="Workspaces"
        >
          {/* Error banner */}
          {(localError || error) && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/10 text-destructive px-3 py-2 text-xs mb-2">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              <span>{localError ?? 'Failed to load workspaces.'}</span>
            </div>
          )}

          {/* Workspace list */}
          {workspaces.length === 0 ? (
            <p className="px-2 py-3 text-sm text-muted-foreground text-center">No workspaces yet.</p>
          ) : (
            <div className="max-h-56 overflow-y-auto space-y-0.5">
              {workspaces.map((workspace) => {
                const isActive = currentWorkspace?.id === workspace.id;
                const isThisSwitching = isSwitching === workspace.id;
                return (
                  <button
                    key={workspace.id}
                    type="button"
                    role="option"
                    aria-selected={isActive}
                    disabled={isThisSwitching}
                    className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors
                      ${isActive ? 'bg-accent text-accent-foreground font-medium' : 'hover:bg-accent hover:text-accent-foreground'}
                      disabled:opacity-60 disabled:cursor-not-allowed`}
                    onClick={() => handleSwitch(workspace.id)}
                  >
                    <span className="truncate">{workspace.name}</span>
                    <span className="flex items-center gap-1.5 shrink-0 ml-2">
                      {workspace.role && (
                        <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
                          {workspace.role}
                        </span>
                      )}
                      {isThisSwitching ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                      ) : isActive ? (
                        <Check className="h-3.5 w-3.5 text-primary" />
                      ) : null}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Divider */}
          <div className="border-t my-1" />

          {/* Create form / button */}
          {isCreating ? (
            <form onSubmit={handleCreate} className="space-y-2 pt-1">
              <input
                ref={inputRef}
                id="new-workspace-name-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Workspace name…"
                maxLength={80}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              <div className="flex gap-2">
                <Button
                  type="submit"
                  size="sm"
                  className="flex-1"
                  disabled={isSubmitting || !name.trim()}
                >
                  {isSubmitting ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                  Create
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => { setIsCreating(false); setLocalError(null); }}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
              </div>
            </form>
          ) : (
            <Button
              id="create-workspace-btn"
              type="button"
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-2"
              onClick={() => setIsCreating(true)}
            >
              <Plus className="h-4 w-4" />
              New workspace
            </Button>
          )}
        </div>
      )}
    </div>
  );
};
