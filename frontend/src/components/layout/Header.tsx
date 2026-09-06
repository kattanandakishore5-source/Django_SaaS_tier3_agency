import React from 'react';
import { Menu, Moon, Sun, User, LogOut } from 'lucide-react';
import { useTheme } from '../ThemeProvider';
import { useAuth } from '../../features/auth/AuthContext';
import { useLogout } from '../../features/auth/hooks';
import { WorkspaceSwitcher } from '../../features/workspaces/WorkspaceSwitcher';
import { Button } from '../ui/Button';

interface HeaderProps {
  onMenuClick: () => void;
  title?: string;
}

export function Header({ onMenuClick, title = 'Dashboard' }: HeaderProps) {
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const logoutMutation = useLogout();
  const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b bg-background px-4 md:px-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="md:hidden" onClick={onMenuClick} aria-label="Toggle Menu">
          <Menu className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold">{title}</h1>
      </div>

      <div className="flex items-center gap-2">
        <WorkspaceSwitcher />

        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>

        <div className="relative">
          <Button
            variant="ghost"
            className="relative h-8 w-8 rounded-full ml-2"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
              <User className="h-4 w-4" />
            </div>
          </Button>
          
          {isDropdownOpen && (
            <>
              <div 
                className="fixed inset-0 z-40" 
                onClick={() => setIsDropdownOpen(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 mt-2 w-56 origin-top-right rounded-md border bg-popover text-popover-foreground shadow-md z-50 animate-in fade-in-80 slide-in-from-top-2">
                <div className="px-4 py-3 border-b">
                  <p className="text-sm font-medium leading-none">{user?.first_name} {user?.last_name}</p>
                  <p className="text-xs text-muted-foreground mt-1 truncate">{user?.email}</p>
                </div>
                <div className="p-1">
                  <button
                    className="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground text-destructive"
                    onClick={() => {
                      logoutMutation.mutate();
                      setIsDropdownOpen(false);
                    }}
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Log out</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
