import { useQuery } from "@tanstack/react-query";
import {
  Hexagon,
  ArrowUpDown,
  Shield,
  Coins,
  ExternalLink,
  TrendingDown,
  CheckCircle2,
  Hash,
  Wallet,
} from "lucide-react";
import { useWallet } from "../hooks/useWallet";

const WAVE_API = import.meta.env.VITE_WAVE_API_URL || "http://localhost:18790";
const HASHSCAN_TESTNET = "https://hashscan.io/testnet";

export default function HederaPage() {
  const wallet = useWallet();

  const { data: _statsResult } = useQuery({
    queryKey: ["hedera", "stats"],
    queryFn: async () => {
      const res = await fetch(`${WAVE_API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "Use hedera_platform_stats tool and return the raw data",
          session_id: "hedera_dashboard",
        }),
      });
      return res.json();
    },
    staleTime: 60 * 1000,
    retry: false,
  });

  const COST_TIERS = [
    { actions: 100, hedera: 0.01, stripe: 1.75, savings: "99.4%" },
    { actions: 1000, hedera: 0.10, stripe: 14.80, savings: "99.3%" },
    { actions: 10000, hedera: 1.00, stripe: 145.30, savings: "99.3%" },
    { actions: 100000, hedera: 10.00, stripe: 1450.30, savings: "99.3%" },
  ];

  const HEDERA_SERVICES = [
    {
      name: "HBAR Micropayments",
      description: "Every AI action ($0.05) settled on-chain for $0.0001 per transaction",
      icon: ArrowUpDown,
      color: "text-green-500",
      bgColor: "bg-green-500/10",
    },
    {
      name: "Consensus Service (HCS)",
      description: "Immutable audit trail — every agent decision timestamped and ordered",
      icon: Shield,
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
    },
    {
      name: "Token Service (HTS)",
      description: "WAVE utility token — users earn rewards for platform activity",
      icon: Coins,
      color: "text-purple-500",
      bgColor: "bg-purple-500/10",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/20">
            <Hexagon className="h-5 w-5 text-purple-500" strokeWidth={1.5} />
          </div>
          <div>
            <h1 className="text-heading text-text-primary">Hedera Dashboard</h1>
            <p className="text-caption text-text-tertiary">
              Blockchain-native billing, audit trail &amp; token economy
            </p>
          </div>
        </div>
        <a
          href={HASHSCAN_TESTNET}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 rounded-md px-3 py-1.5 text-caption text-text-secondary border border-border hover:bg-accent-subtle transition-colors"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          HashScan Explorer
        </a>
      </div>

      {/* Wallet Connection */}
      <div className="rounded-xl border border-border bg-surface p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-500/10">
              <Wallet className="h-4 w-4 text-orange-500" />
            </div>
            <div>
              <h3 className="text-body-medium text-text-primary font-medium">
                MetaMask Wallet
              </h3>
              <p className="text-caption text-text-tertiary">
                {wallet.address
                  ? "Connected to Hedera " + (wallet.chainId === 296 ? "Testnet" : "Mainnet")
                  : "Connect to pay for AI actions with HBAR"}
              </p>
            </div>
          </div>

          {wallet.address ? (
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-body-medium font-mono text-text-primary">
                  {wallet.shortAddress}
                </p>
                <p className="text-caption text-text-tertiary">
                  {wallet.balance ? `${parseFloat(wallet.balance).toFixed(4)} HBAR` : "Loading..."}
                </p>
              </div>
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            </div>
          ) : (
            <button
              onClick={wallet.connect}
              disabled={wallet.isConnecting}
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 px-4 py-2 text-caption font-medium text-white hover:from-orange-600 hover:to-amber-600 transition-all disabled:opacity-50"
            >
              <Wallet className="h-3.5 w-3.5" />
              {wallet.isConnecting ? "Connecting..." : "Connect MetaMask"}
            </button>
          )}
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {HEDERA_SERVICES.map((service) => (
          <div
            key={service.name}
            className="rounded-xl border border-border bg-surface p-5 space-y-3"
          >
            <div className="flex items-center gap-3">
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-lg ${service.bgColor}`}
              >
                <service.icon className={`h-4 w-4 ${service.color}`} />
              </div>
              <h3 className="text-body-medium text-text-primary font-medium">
                {service.name}
              </h3>
            </div>
            <p className="text-caption text-text-secondary">
              {service.description}
            </p>
          </div>
        ))}
      </div>

      {/* Cost Comparison */}
      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-green-500" />
            <h2 className="text-body-medium text-text-primary font-medium">
              Micropayment Cost Savings
            </h2>
          </div>
          <span className="rounded-full bg-green-500/10 px-3 py-1 text-caption font-semibold text-green-600">
            99.3% cheaper
          </span>
        </div>
        <div className="p-5">
          <div className="overflow-x-auto">
            <table className="w-full text-caption">
              <thead>
                <tr className="text-text-tertiary text-left">
                  <th className="pb-3 font-medium">AI Actions/month</th>
                  <th className="pb-3 font-medium">Revenue</th>
                  <th className="pb-3 font-medium">Stripe Cost</th>
                  <th className="pb-3 font-medium">Hedera Cost</th>
                  <th className="pb-3 font-medium">Savings</th>
                </tr>
              </thead>
              <tbody className="text-text-primary">
                {COST_TIERS.map((tier) => (
                  <tr key={tier.actions} className="border-t border-border-subtle">
                    <td className="py-3 font-medium">
                      {tier.actions.toLocaleString()}
                    </td>
                    <td className="py-3">
                      ${(tier.actions * 0.05).toLocaleString()}
                    </td>
                    <td className="py-3 text-red-400 line-through">
                      ${tier.stripe.toFixed(2)}
                    </td>
                    <td className="py-3 text-green-500 font-semibold">
                      ${tier.hedera.toFixed(2)}
                    </td>
                    <td className="py-3">
                      <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-[11px] font-semibold text-green-600">
                        {tier.savings}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-caption text-text-tertiary">
            Each AI action costs $0.05. Hedera transaction fee: ~$0.0001. Traditional
            processors charge 2.9% + $0.30 per charge, making micropayments impossible.
          </p>
        </div>
      </div>

      {/* How It Works */}
      <div className="rounded-xl border border-border bg-surface p-5 space-y-4">
        <h2 className="text-body-medium text-text-primary font-medium">
          How Hedera Integration Works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            {
              step: "1",
              title: "AI Action",
              desc: "Wave executes a tool (caption, compliance, prospect)",
              icon: Coins,
            },
            {
              step: "2",
              title: "HBAR Payment",
              desc: "$0.05 settled as HBAR micropayment on-chain",
              icon: ArrowUpDown,
            },
            {
              step: "3",
              title: "HCS Audit",
              desc: "Action logged to Hedera Consensus Service (immutable)",
              icon: Shield,
            },
            {
              step: "4",
              title: "WAVE Reward",
              desc: "User earns WAVE tokens for platform activity",
              icon: CheckCircle2,
            },
          ].map((item) => (
            <div key={item.step} className="text-center space-y-2">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-accent/10 text-accent font-bold text-body">
                {item.step}
              </div>
              <h4 className="text-body-medium text-text-primary font-medium">
                {item.title}
              </h4>
              <p className="text-caption text-text-tertiary">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Agent Tools */}
      <div className="rounded-xl border border-border bg-surface p-5 space-y-3">
        <h2 className="text-body-medium text-text-primary font-medium">
          Wave's Hedera Tools
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { name: "hedera_check_balance", desc: "Check HBAR and WAVE token balances" },
            { name: "hedera_audit_trail", desc: "Read immutable HCS audit log" },
            { name: "hedera_verify_transaction", desc: "Verify any on-chain transaction" },
            { name: "hedera_recent_transactions", desc: "View recent micropayments" },
            { name: "hedera_platform_stats", desc: "Full platform blockchain health" },
            { name: "hedera_cost_report", desc: "Compare costs vs traditional billing" },
          ].map((tool) => (
            <div
              key={tool.name}
              className="flex items-center gap-3 rounded-lg border border-border-subtle px-3 py-2"
            >
              <Hash className="h-3.5 w-3.5 text-purple-500 shrink-0" />
              <div>
                <code className="text-[11px] text-accent">{tool.name}</code>
                <p className="text-caption text-text-tertiary">{tool.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
