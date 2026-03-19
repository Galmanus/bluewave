import { useQuery, useMutation } from "@tanstack/react-query";
import { CreditCard, ExternalLink, TrendingUp, Users, Zap, HardDrive } from "lucide-react";
import api from "../lib/api";

interface PlanInfo {
  plan: string;
  is_active: boolean;
  max_users: number;
  max_ai_actions_month: number;
  max_storage_bytes: number;
  current_period_start: string | null;
  current_period_end: string | null;
  stripe_customer_id: string | null;
}

interface UsageInfo {
  ai_actions_used: number;
  ai_actions_limit: number;
  storage_used_bytes: number;
  storage_limit_bytes: number;
  users_count: number;
  users_limit: number;
}

interface PlanSummary {
  plan: PlanInfo;
  usage: UsageInfo;
}

interface Invoice {
  id: string;
  status: string;
  amount_due: number;
  currency: string;
  created: number;
  hosted_invoice_url: string | null;
}

const PLAN_TIERS = [
  {
    name: "Free",
    key: "free",
    price: "$0",
    features: ["3 team members", "50 AI actions/month", "5 GB storage"],
  },
  {
    name: "Pro",
    key: "pro",
    price: "$49/mo",
    features: ["Unlimited team members", "Unlimited AI actions", "100 GB storage", "Priority support"],
  },
  {
    name: "Business",
    key: "business",
    price: "$149/mo",
    features: ["Everything in Pro", "500 GB storage", "Custom branding", "API access"],
  },
  {
    name: "Enterprise",
    key: "enterprise",
    price: "Custom",
    features: ["Everything in Business", "Unlimited storage", "Dedicated support", "SLA guarantee"],
  },
];

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function ProgressBar({ used, limit, label }: { used: number; limit: number; label: string }) {
  const pct = limit === 0 ? 0 : Math.min((used / limit) * 100, 100);
  const isUnlimited = limit === 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className="font-medium">
          {isUnlimited ? `${used} / Unlimited` : `${used} / ${limit}`}
        </span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${pct > 90 ? "bg-red-500" : pct > 70 ? "bg-yellow-500" : "bg-blue-500"}`}
          style={{ width: isUnlimited ? "0%" : `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function BillingPage() {
  const { data, isLoading } = useQuery<PlanSummary>({
    queryKey: ["billing", "plan"],
    queryFn: () => api.get("/billing/plan").then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: invoices } = useQuery<Invoice[]>({
    queryKey: ["billing", "invoices"],
    queryFn: () => api.get("/billing/invoices").then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const checkoutMutation = useMutation({
    mutationFn: (targetPlan: string) =>
      api.post("/billing/checkout", {
        target_plan: targetPlan,
        success_url: `${window.location.origin}/billing?success=true`,
        cancel_url: `${window.location.origin}/billing`,
      }).then((r) => r.data),
    onSuccess: (data: { url: string }) => {
      window.location.href = data.url;
    },
  });

  const portalMutation = useMutation({
    mutationFn: () =>
      api.post("/billing/portal", {
        return_url: `${window.location.origin}/billing`,
      }).then((r) => r.data),
    onSuccess: (data: { url: string }) => {
      window.location.href = data.url;
    },
  });

  if (isLoading || !data) {
    return (
      <div className="p-6 animate-pulse">
        <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded mb-6" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const { plan, usage } = data;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Billing & Plan</h1>
        {plan.stripe_customer_id && (
          <button
            onClick={() => portalMutation.mutate()}
            disabled={portalMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition"
          >
            <CreditCard className="w-4 h-4" />
            Manage Subscription
            <ExternalLink className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Current Plan */}
      <div className="bg-white dark:bg-gray-900 border dark:border-gray-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Zap className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h2 className="font-semibold text-lg">
              {plan.plan.charAt(0).toUpperCase() + plan.plan.slice(1)} Plan
            </h2>
            <p className="text-sm text-gray-500">
              {plan.is_active ? "Active" : "Inactive"}
              {plan.current_period_end && ` — renews ${new Date(plan.current_period_end).toLocaleDateString()}`}
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <TrendingUp className="w-4 h-4 text-gray-500" />
            <ProgressBar
              used={usage.ai_actions_used}
              limit={usage.ai_actions_limit}
              label="AI Actions"
            />
          </div>
          <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <HardDrive className="w-4 h-4 text-gray-500" />
            <ProgressBar
              used={Number(formatBytes(usage.storage_used_bytes).split(" ")[0])}
              limit={Number(formatBytes(usage.storage_limit_bytes).split(" ")[0])}
              label={`Storage (${formatBytes(usage.storage_used_bytes)} / ${usage.storage_limit_bytes === 0 ? "Unlimited" : formatBytes(usage.storage_limit_bytes)})`}
            />
          </div>
          <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <Users className="w-4 h-4 text-gray-500" />
            <ProgressBar
              used={usage.users_count}
              limit={usage.users_limit}
              label="Team Members"
            />
          </div>
        </div>
      </div>

      {/* Pricing Tiers */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Plans</h2>
        <div className="grid gap-4 md:grid-cols-4">
          {PLAN_TIERS.map((tier) => {
            const isCurrent = tier.key === plan.plan;
            return (
              <div
                key={tier.key}
                className={`border rounded-xl p-5 flex flex-col ${
                  isCurrent
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                    : "border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900"
                }`}
              >
                <h3 className="font-semibold text-lg">{tier.name}</h3>
                <p className="text-2xl font-bold mt-1 mb-3">{tier.price}</p>
                <ul className="space-y-1.5 text-sm text-gray-600 dark:text-gray-400 flex-1">
                  {tier.features.map((f) => (
                    <li key={f}>&#10003; {f}</li>
                  ))}
                </ul>
                {isCurrent ? (
                  <div className="mt-4 text-center text-sm font-medium text-blue-600">
                    Current Plan
                  </div>
                ) : tier.key !== "free" ? (
                  <button
                    onClick={() => checkoutMutation.mutate(tier.key)}
                    disabled={checkoutMutation.isPending}
                    className="mt-4 w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium disabled:opacity-50"
                  >
                    {checkoutMutation.isPending ? "Redirecting..." : "Upgrade"}
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      {/* Invoices */}
      {invoices && invoices.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Invoice History</h2>
          <div className="bg-white dark:bg-gray-900 border dark:border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500">
                <tr>
                  <th className="text-left p-3">Date</th>
                  <th className="text-left p-3">Amount</th>
                  <th className="text-left p-3">Status</th>
                  <th className="text-right p-3">Link</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id} className="border-t dark:border-gray-800">
                    <td className="p-3">{new Date(inv.created * 1000).toLocaleDateString()}</td>
                    <td className="p-3">${(inv.amount_due / 100).toFixed(2)} {inv.currency.toUpperCase()}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${inv.status === "paid" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      {inv.hosted_invoice_url && (
                        <a
                          href={inv.hosted_invoice_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          View
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
