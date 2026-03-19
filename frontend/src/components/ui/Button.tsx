import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Slot } from "@radix-ui/react-slot";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/cn";

const variants = {
  primary:
    "bg-accent text-white hover:bg-accent-hover shadow-xs active:scale-[0.98]",
  secondary:
    "border border-border bg-surface text-text-primary hover:bg-accent-subtle active:scale-[0.98]",
  ghost:
    "text-text-secondary hover:bg-accent-subtle hover:text-text-primary",
  danger:
    "bg-danger text-white hover:bg-red-700 dark:hover:bg-red-500 active:scale-[0.98]",
  "danger-outline":
    "border border-danger/30 text-danger hover:bg-danger-subtle active:scale-[0.98]",
};

const sizes = {
  sm: "h-8 px-3 text-caption gap-1.5",
  md: "h-9 px-4 text-body-medium gap-2",
  lg: "h-10 px-5 text-body-medium gap-2",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  loading?: boolean;
  asChild?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      asChild = false,
      children,
      ...props
    },
    ref
  ) => {
    if (asChild) {
      return (
        <Slot
          ref={ref}
          className={cn(
            "inline-flex items-center justify-center rounded-md font-medium transition-all duration-150 ease-smooth focus-ring disabled:pointer-events-none disabled:opacity-40",
            variants[variant],
            sizes[size],
            className
          )}
          {...props}
        >
          {children}
        </Slot>
      );
    }
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          "inline-flex items-center justify-center rounded-md font-medium transition-all duration-150 ease-smooth focus-ring disabled:pointer-events-none disabled:opacity-40",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button, type ButtonProps };
