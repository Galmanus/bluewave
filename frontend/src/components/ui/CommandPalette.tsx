import { Command } from "cmdk";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Images, Upload, Users, Search, Moon, Sun } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { cn } from "../../lib/cn";

const ROLE_LEVEL: Record<string, number> = {
  viewer: 0,
  editor: 1,
  admin: 2,
};

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const userLevel = ROLE_LEVEL[user?.role ?? "viewer"] ?? 0;

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  function go(path: string) {
    navigate(path);
    setOpen(false);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/40 animate-fade-in"
        onClick={() => setOpen(false)}
      />
      <div className="flex items-start justify-center pt-[20vh]">
        <Command
          className={cn(
            "relative w-full max-w-lg rounded-xl border border-border bg-surface shadow-lg animate-slide-up",
            "overflow-hidden"
          )}
        >
          <div className="flex items-center gap-2 border-b border-border-subtle px-4">
            <Search className="h-4 w-4 text-text-tertiary" strokeWidth={1.5} />
            <Command.Input
              placeholder="Type a command or search..."
              className="flex h-12 w-full bg-transparent text-body text-text-primary placeholder:text-text-tertiary outline-none"
              autoFocus
            />
            <kbd className="hidden rounded border border-border px-1.5 py-0.5 text-[10px] text-text-tertiary sm:inline">
              ESC
            </kbd>
          </div>
          <Command.List className="max-h-72 overflow-auto p-2">
            <Command.Empty className="py-6 text-center text-body text-text-tertiary">
              No results found.
            </Command.Empty>
            <Command.Group
              heading="Navigation"
              className="px-2 py-1.5 text-caption font-medium text-text-tertiary"
            >
              <Command.Item
                onSelect={() => go("/assets")}
                className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-body text-text-primary aria-selected:bg-accent-subtle aria-selected:text-accent"
              >
                <Images className="h-4 w-4" strokeWidth={1.5} />
                Assets
              </Command.Item>
              {userLevel >= 1 && (
                <Command.Item
                  onSelect={() => go("/assets/upload")}
                  className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-body text-text-primary aria-selected:bg-accent-subtle aria-selected:text-accent"
                >
                  <Upload className="h-4 w-4" strokeWidth={1.5} />
                  Upload Asset
                </Command.Item>
              )}
              {userLevel >= 2 && (
                <Command.Item
                  onSelect={() => go("/team")}
                  className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-body text-text-primary aria-selected:bg-accent-subtle aria-selected:text-accent"
                >
                  <Users className="h-4 w-4" strokeWidth={1.5} />
                  Team
                </Command.Item>
              )}
            </Command.Group>
            <Command.Separator className="my-1 h-px bg-border-subtle" />
            <Command.Group
              heading="Settings"
              className="px-2 py-1.5 text-caption font-medium text-text-tertiary"
            >
              <Command.Item
                onSelect={() => {
                  toggleTheme();
                  setOpen(false);
                }}
                className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-body text-text-primary aria-selected:bg-accent-subtle aria-selected:text-accent"
              >
                {theme === "dark" ? (
                  <Sun className="h-4 w-4" strokeWidth={1.5} />
                ) : (
                  <Moon className="h-4 w-4" strokeWidth={1.5} />
                )}
                Toggle {theme === "dark" ? "light" : "dark"} mode
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
