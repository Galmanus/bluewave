import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, CheckCircle, Clock, FileImage, Shield, Sparkles } from "lucide-react";
import api from "../lib/api";
import StatCard from "../components/analytics/StatCard";
import TeamTable from "../components/analytics/TeamTable";
import ROICard from "../components/analytics/ROICard";

const PERIOD_OPTIONS = [
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
  { label: "90 days", value: 90 },
];

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);

  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: ["analytics", "overview", days],
    queryFn: () => api.get(`/analytics/overview?days=${days}`).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: trends } = useQuery({
    queryKey: ["analytics", "trends", days],
    queryFn: () => api.get(`/analytics/trends?days=${Math.max(days, 14)}`).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: team } = useQuery({
    queryKey: ["analytics", "team", days],
    queryFn: () => api.get(`/analytics/team?days=${days}`).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: aiUsage } = useQuery({
    queryKey: ["analytics", "ai", days],
    queryFn: () => api.get(`/analytics/ai?days=${days}`).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: roi } = useQuery({
    queryKey: ["analytics", "roi", days],
    queryFn: () => api.get(`/analytics/roi?days=${days}`).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  if (loadingOverview) {
    return (
      <div className="p-6 animate-pulse space-y-6">
        <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-gray-200 dark:bg-gray-700 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setDays(opt.value)}
              className={`px-3 py-1.5 text-sm rounded-md transition ${
                days === opt.value
                  ? "bg-white dark:bg-gray-700 shadow text-blue-600 font-medium"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="Total Assets"
            value={overview.total_assets}
            icon={FileImage}
          />
          <StatCard
            title="Approved"
            value={overview.total_approved}
            subtitle={overview.total_assets > 0
              ? `${Math.round((overview.total_approved / overview.total_assets) * 100)}% approval rate`
              : undefined}
            icon={CheckCircle}
          />
          <StatCard
            title="Compliance Score"
            value={overview.compliance_avg_score !== null ? `${overview.compliance_avg_score}` : "N/A"}
            subtitle="average score"
            icon={Shield}
          />
          <StatCard
            title="AI Actions"
            value={overview.ai_actions_count}
            subtitle={`$${(overview.ai_cost_cents / 100).toFixed(2)} total cost`}
            icon={Sparkles}
          />
        </div>
      )}

      {/* Main content grid */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* Trend Chart (simplified — bar chart with CSS) */}
        <div className="md:col-span-2 bg-white dark:bg-gray-900 border dark:border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4" /> Weekly Trends
          </h2>
          {trends && trends.length > 0 ? (
            <div className="space-y-2">
              <div className="flex items-end gap-1 h-40">
                {trends.slice(-12).map((point: { period: string; uploads: number; approvals: number }, i: number) => {
                  const maxVal = Math.max(...trends.slice(-12).map((p: { uploads: number }) => p.uploads), 1);
                  const height = (point.uploads / maxVal) * 100;
                  const approvalHeight = (point.approvals / maxVal) * 100;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-0.5" title={`${point.period}: ${point.uploads} uploads, ${point.approvals} approved`}>
                      <div className="w-full flex flex-col justify-end h-full gap-0.5">
                        <div
                          className="w-full bg-blue-500 rounded-t"
                          style={{ height: `${height}%`, minHeight: point.uploads > 0 ? "4px" : "0" }}
                        />
                        <div
                          className="w-full bg-green-500 rounded-t"
                          style={{ height: `${approvalHeight}%`, minHeight: point.approvals > 0 ? "4px" : "0" }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between text-xs text-gray-400">
                <span>{trends[Math.max(0, trends.length - 12)]?.period}</span>
                <span>{trends[trends.length - 1]?.period}</span>
              </div>
              <div className="flex gap-4 text-xs mt-2">
                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500 rounded" /> Uploads</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-500 rounded" /> Approved</span>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No trend data available for this period.</p>
          )}
        </div>

        {/* ROI Card */}
        {roi && <ROICard data={roi} />}
      </div>

      {/* AI Usage Breakdown */}
      {aiUsage && Object.keys(aiUsage.actions_by_type).length > 0 && (
        <div className="bg-white dark:bg-gray-900 border dark:border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Sparkles className="w-4 h-4" /> AI Usage by Type
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(aiUsage.actions_by_type).map(([type, count]) => (
              <div key={type} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-xl font-bold">{count as number}</p>
                <p className="text-xs text-gray-500 capitalize">{type.replace("_", " ")}</p>
              </div>
            ))}
          </div>
          <div className="mt-3 text-sm text-gray-500">
            Avg cost per asset: ${aiUsage.avg_cost_per_asset_cents ? (aiUsage.avg_cost_per_asset_cents / 100).toFixed(3) : "0.00"}
          </div>
        </div>
      )}

      {/* Team Productivity */}
      <div>
        <h2 className="font-semibold mb-3 flex items-center gap-2">
          <Clock className="w-4 h-4" /> Team Productivity
        </h2>
        {team && <TeamTable members={team} />}
      </div>
    </div>
  );
}
