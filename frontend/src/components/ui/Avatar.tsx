import { cn } from "../../lib/cn";

const roleColors: Record<string, string> = {
  admin: "bg-accent-subtle text-accent",
  editor: "bg-success-subtle text-success",
  viewer: "bg-[var(--border-subtle)] text-text-secondary",
};

interface AvatarProps {
  name: string;
  role?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Avatar({ name, role, size = "md", className }: AvatarProps) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const sizeClasses = {
    sm: "h-7 w-7 text-[10px]",
    md: "h-8 w-8 text-caption",
    lg: "h-10 w-10 text-body-medium",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center justify-center rounded-full font-semibold",
        sizeClasses[size],
        role ? roleColors[role] || roleColors.viewer : "bg-accent-subtle text-accent",
        className
      )}
      aria-label={name}
    >
      {initials}
    </div>
  );
}
