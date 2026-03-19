import * as TabsPrimitive from "@radix-ui/react-tabs";
import { motion } from "framer-motion";
import { cn } from "../../lib/cn";

interface Tab {
  value: string;
  label: string;
  count?: number;
}

interface TabsProps {
  tabs: Tab[];
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
  layoutId?: string;
}

export function Tabs({
  tabs,
  value,
  onValueChange,
  children,
  className,
  layoutId = "tab-indicator",
}: TabsProps) {
  return (
    <TabsPrimitive.Root value={value} onValueChange={onValueChange}>
      <TabsPrimitive.List
        className={cn(
          "flex gap-1 border-b border-border-subtle",
          className
        )}
      >
        {tabs.map((tab) => {
          const isActive = value === tab.value;
          return (
            <TabsPrimitive.Trigger
              key={tab.value}
              value={tab.value}
              className="relative px-4 py-2.5 text-body-medium transition-colors outline-none"
            >
              <span
                className={
                  isActive
                    ? "text-accent"
                    : "text-text-tertiary hover:text-text-secondary"
                }
              >
                {tab.label}
                {tab.count !== undefined && (
                  <span className="ml-1.5 rounded-full bg-border-subtle px-1.5 py-0.5 text-caption">
                    {tab.count}
                  </span>
                )}
              </span>
              {isActive && (
                <motion.div
                  layoutId={layoutId}
                  className="absolute inset-x-0 -bottom-px h-0.5 bg-accent"
                  transition={{ type: "spring", stiffness: 500, damping: 35 }}
                />
              )}
            </TabsPrimitive.Trigger>
          );
        })}
      </TabsPrimitive.List>
      {children}
    </TabsPrimitive.Root>
  );
}

export const TabsContent = TabsPrimitive.Content;
