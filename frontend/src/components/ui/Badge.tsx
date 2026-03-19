import { cn } from "../../lib/cn";

const badgeVariants = {
  default: "bg-accent-subtle text-accent",
  draft: "bg-[var(--border-subtle)] text-text-secondary",
  pending_approval: "bg-warning-subtle text-warning",
  approved: "bg-success-subtle text-success",
  danger: "bg-danger-subtle text-danger",
  admin: "bg-accent-subtle text-accent",
  editor: "bg-success-subtle text-success",
  viewer: "bg-[var(--border-subtle)] text-text-secondary",
};

interface BadgeProps {
  variant?: keyof typeof badgeVariants;
  dot?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function Badge({
  variant = "default",
  dot = false,
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-caption font-medium",
        badgeVariants[variant],
        className
      )}
    >
      {dot && (
        <span
          className="h-1.5 w-1.5 rounded-full bg-current"
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}
