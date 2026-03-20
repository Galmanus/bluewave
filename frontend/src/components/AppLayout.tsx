import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Images,
  Upload,
  Users,
  Menu,
  X,
  LogOut,
  Moon,
  Sun,
  ChevronLeft,
  Waves,
  Search,
  Webhook,
  TrendingUp,
  Palette,
  Bot,
  BarChart3,
  Calendar,
  Dna,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import { useAssetCounts } from "../hooks/useAssets";
import { Avatar } from "./ui/Avatar";
import { Badge } from "./ui/Badge";
import { Tooltip } from "./ui/Tooltip";
import { CommandPalette } from "./ui/CommandPalette";
import { cn } from "../lib/cn";

const NAV_ITEMS = [
  { to: "/assets", label: "Assets", icon: Images, minRole: "viewer" },
  { to: "/assets/upload", label: "Upload", icon: Upload, minRole: "editor" },
  { to: "/wave", label: "Guardian", icon: Bot, minRole: "editor" },
  { to: "/trends", label: "Trends", icon: TrendingUp, minRole: "editor" },
  { to: "/calendar", label: "Calendar", icon: Calendar, minRole: "editor" },
  { to: "/brand", label: "Brand", icon: Palette, minRole: "admin" },
  { to: "/brand-dna", label: "Brand DNA", icon: Dna, minRole: "admin" },
  { to: "/analytics", label: "Analytics", icon: BarChart3, minRole: "admin" },
  { to: "/team", label: "Team", icon: Users, minRole: "admin" },
  { to: "/integrations", label: "Integrations", icon: Webhook, minRole: "admin" },
];

const ROLE_LEVEL: Record<string, number> = {
  viewer: 0,
  editor: 1,
  admin: 2,
};

export default function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const { data: counts } = useAssetCounts();
  const pendingCount = counts?.pending_approval ?? 0;

  if (!user) return null;

  const userLevel = ROLE_LEVEL[user.role] ?? 0;
  const filteredNav = NAV_ITEMS.filter(
    (item) => userLevel >= (ROLE_LEVEL[item.minRole] ?? 0)
  );

  const sidebarWidth = collapsed ? "w-16" : "w-60";

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/40 md:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border bg-surface transition-all duration-200 ease-smooth md:static",
          sidebarWidth,
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center justify-between border-b border-border-subtle px-4">
          <Link to="/" className="flex items-center gap-2">
            <Waves className="h-5 w-5 text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.6)]" />
            {!collapsed && (
              <span className="text-subheading font-extrabold tracking-tight bg-gradient-to-r from-cyan-300 via-blue-400 to-cyan-300 bg-clip-text text-transparent" style={{backgroundSize: '200% auto', animation: 'shimmer 3s linear infinite'}}>
                Bluewave
              </span>
            )}
          </Link>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden rounded-md p-1 text-text-tertiary hover:bg-accent-subtle hover:text-text-primary md:block"
          >
            <ChevronLeft
              className={cn(
                "h-4 w-4 transition-transform duration-200",
                collapsed && "rotate-180"
              )}
            />
          </button>
          <button
            onClick={() => setMobileOpen(false)}
            className="rounded-md p-1 text-text-tertiary hover:text-text-primary md:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-1 p-2">
          {filteredNav.map((item) => {
            const isActive = item.to === "/assets"
              ? location.pathname === "/assets" || (location.pathname.startsWith("/assets/") && !location.pathname.startsWith("/assets/upload"))
              : location.pathname.startsWith(item.to);
            const Icon = item.icon;
            const link = (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-body-medium transition-colors duration-150",
                  isActive
                    ? "bg-accent-subtle text-accent"
                    : "text-text-secondary hover:bg-accent-subtle hover:text-text-primary"
                )}
              >
                <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.5} />
                {!collapsed && <span className="flex-1">{item.label}</span>}
                {!collapsed && item.to === "/assets" && pendingCount > 0 && (
                  <span className="ml-auto rounded-full bg-warning/10 px-1.5 py-0.5 text-[10px] font-semibold text-warning">
                    {pendingCount}
                  </span>
                )}
              </Link>
            );
            return collapsed ? (
              <Tooltip key={item.to} content={item.label} side="right">
                {link}
              </Tooltip>
            ) : (
              link
            );
          })}
        </nav>

        {/* Bottom: user + theme */}
        <div className="border-t border-border-subtle p-3 space-y-2">
          <button
            onClick={toggleTheme}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-body text-text-secondary hover:bg-accent-subtle hover:text-text-primary transition-colors"
          >
            {theme === "dark" ? (
              <Sun className="h-[18px] w-[18px] shrink-0" strokeWidth={1.5} />
            ) : (
              <Moon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.5} />
            )}
            {!collapsed && <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>}
          </button>
          <div className="flex items-center gap-3 rounded-md px-3 py-2">
            <Avatar name={user.full_name} role={user.role} size="sm" />
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="truncate text-body-medium text-text-primary">
                  {user.full_name}
                </p>
                <p className="truncate text-caption text-text-tertiary">
                  {user.role}
                </p>
              </div>
            )}
            {!collapsed && (
              <Tooltip content="Logout">
                <button
                  onClick={logout}
                  className="rounded-md p-1 text-text-tertiary hover:text-danger transition-colors"
                  aria-label="Logout"
                >
                  <LogOut className="h-4 w-4" strokeWidth={1.5} />
                </button>
              </Tooltip>
            )}
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4 md:px-xl">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-1.5 text-text-secondary hover:bg-accent-subtle md:hidden"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" strokeWidth={1.5} />
          </button>
          <button
            onClick={() => {
              const e = new KeyboardEvent("keydown", { key: "k", metaKey: true });
              document.dispatchEvent(e);
            }}
            className="hidden items-center gap-2 rounded-md border border-border px-3 py-1.5 text-caption text-text-tertiary hover:bg-accent-subtle hover:text-text-primary transition-colors md:flex"
          >
            <Search className="h-3.5 w-3.5" strokeWidth={1.5} />
            Search...
            <kbd className="ml-2 rounded border border-border px-1 py-0.5 text-[10px]">
              ⌘K
            </kbd>
          </button>
          <div className="flex items-center gap-3">
            <Badge variant={user.role as "admin" | "editor" | "viewer"} dot>
              {user.role}
            </Badge>
          </div>
        </header>

        {/* Page */}
        <main className="flex-1 overflow-auto">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            className="p-lg md:p-xl"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>

      {/* Command Palette */}
      <CommandPalette />
    </div>
  );
}
