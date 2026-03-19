import { type LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: number; // percentage change, positive = good
}

export default function StatCard({ title, value, subtitle, icon: Icon, trend }: StatCardProps) {
  return (
    <div className="bg-white dark:bg-gray-900 border dark:border-gray-800 rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <Icon className="w-5 h-5 text-blue-600" />
        </div>
      </div>
      {trend !== undefined && (
        <div className={`mt-2 text-xs font-medium ${trend >= 0 ? "text-green-600" : "text-red-500"}`}>
          {trend >= 0 ? "+" : ""}{trend}% vs previous period
        </div>
      )}
    </div>
  );
}
