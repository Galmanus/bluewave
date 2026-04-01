import { useState } from "react";
import { motion } from "framer-motion";
import { Check, CreditCard, QrCode, Loader2, Crown, Zap, Building2 } from "lucide-react";
import { useGeo } from "../contexts/GeoContext";
import api from "../lib/api";
import { toast } from "sonner";

export default function BillingPage() {
  const { geo } = useGeo();
  const p = geo.lang === "pt";

  const [loading, setLoading] = useState<string | null>(null);
  const [pixData, setPixData] = useState<{
    success: boolean;
    qr_code?: string;
    qr_code_base64?: string;
    ticket_url?: string;
    payment_id?: string;
    error?: string;
  } | null>(null);

  const plans = [
    {
      id: "free",
      name: p ? "Grátis" : "Free",
      price: p ? "R$0" : "$0",
      period: p ? "/mês" : "/month",
      icon: Check,
      features: p
        ? ["1 marca", "50 checks/mês", "Captions automáticos", "Workflows de aprovação"]
        : ["1 brand", "50 checks/month", "AI captions", "Approval workflows"],
      current: true,
    },
    {
      id: "pro",
      name: "Pro",
      price: p ? "R$197" : "$39",
      period: p ? "/mês" : "/month",
      icon: Zap,
      features: p
        ? ["3 marcas", "Checks ilimitados", "Gerador de conteúdo (10 tipos)", "Certificados de compliance", "Calendário social", "Acesso à API"]
        : ["3 brands", "Unlimited checks", "Content generator (10 types)", "Compliance certificates", "Social calendar", "API access"],
      highlighted: true,
      badge: p ? "Mais popular" : "Most popular",
    },
    {
      id: "agency",
      name: p ? "Agência" : "Agency",
      price: p ? "R$497" : "$99",
      period: p ? "/mês" : "/month",
      icon: Building2,
      features: p
        ? ["Marcas ilimitadas", "Extração de Brand DNA", "White-label para clientes", "R$97/cliente adicional", "Wave autônomo (89 tools)", "Suporte prioritário"]
        : ["Unlimited brands", "Brand DNA extraction", "White-label for clients", "$19/additional client", "Autonomous Wave (89 tools)", "Priority support"],
    },
  ];

  async function handlePix(planId: string) {
    setLoading(planId);
    try {
      const { data } = await api.post("/payments/pix", { plan: planId });
      if (data.success) {
        setPixData(data);
        toast.success(p ? "QR Code Pix gerado!" : "Pix QR code generated!");
      } else {
        toast.error(data.error || "Failed");
      }
    } catch (e: unknown) {
      const axiosErr = e as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr.response?.data?.detail || (p ? "Erro ao gerar Pix" : "Error generating Pix"));
    }
    setLoading(null);
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-xl">
        <h1 className="text-heading text-text-primary">
          {p ? "Plano e Pagamento" : "Plan & Billing"}
        </h1>
        <p className="text-body text-text-secondary mt-1">
          {p ? "Gerencie seu plano e forma de pagamento." : "Manage your plan and payment method."}
        </p>
      </div>

      {/* Current plan */}
      <div className="rounded-xl border border-border bg-surface p-lg mb-xl">
        <div className="flex items-center gap-3">
          <Crown className="h-5 w-5 text-amber-400" />
          <div>
            <p className="text-body-medium text-text-primary">
              {p ? "Plano atual" : "Current plan"}: <strong>{p ? "Grátis" : "Free"}</strong>
            </p>
            <p className="text-caption text-text-tertiary">
              {p ? "50 checks de compliance por mês" : "50 compliance checks per month"}
            </p>
          </div>
        </div>
      </div>

      {/* Plans grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-lg">
        {plans.map((plan, i) => (
          <motion.div
            key={plan.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`relative rounded-xl p-lg ${
              plan.highlighted
                ? "border-2 border-accent bg-accent-subtle"
                : "border border-border bg-surface"
            }`}
          >
            {plan.badge && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-[10px] font-semibold bg-accent text-white">
                {plan.badge}
              </span>
            )}

            <plan.icon className="h-6 w-6 text-accent mb-3" />
            <h3 className="text-subheading text-text-primary">{plan.name}</h3>
            <div className="mt-2 mb-4">
              <span className="text-display text-text-primary">{plan.price}</span>
              <span className="text-body text-text-tertiary">{plan.period}</span>
            </div>

            <ul className="space-y-2 mb-6">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-caption text-text-secondary">
                  <Check className="h-3.5 w-3.5 text-success shrink-0 mt-0.5" />
                  {f}
                </li>
              ))}
            </ul>

            {plan.current ? (
              <div className="text-center text-caption text-text-tertiary py-2">
                {p ? "Plano atual" : "Current plan"}
              </div>
            ) : p ? (
              <div className="space-y-2">
                <button
                  onClick={() => handlePix(plan.id)}
                  disabled={!!loading}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-accent text-white font-medium text-body hover:bg-accent-hover transition-all disabled:opacity-40"
                >
                  {loading === plan.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <QrCode className="h-4 w-4" />
                  )}
                  Pagar com Pix
                </button>
                <button className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-border text-text-secondary text-caption hover:bg-surface-elevated transition-all">
                  <CreditCard className="h-3.5 w-3.5" />
                  Cartão (até 12x)
                </button>
              </div>
            ) : (
              <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-accent text-white font-medium text-body hover:bg-accent-hover transition-all">
                <CreditCard className="h-4 w-4" />
                Upgrade
              </button>
            )}
          </motion.div>
        ))}
      </div>

      {/* Pix QR Code modal */}
      {pixData && pixData.qr_code && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setPixData(null)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-surface rounded-2xl p-xl max-w-sm w-full mx-4 shadow-lg border border-border"
          >
            <h3 className="text-heading text-text-primary text-center mb-4">
              {p ? "Pague com Pix" : "Pay with Pix"}
            </h3>

            {pixData.qr_code_base64 && (
              <img
                src={`data:image/png;base64,${pixData.qr_code_base64}`}
                alt="Pix QR Code"
                className="w-48 h-48 mx-auto mb-4 rounded-lg"
              />
            )}

            <div className="mb-4">
              <p className="text-caption text-text-tertiary mb-1 text-center">
                {p ? "Ou copie o código:" : "Or copy the code:"}
              </p>
              <div
                className="bg-surface-elevated rounded-lg p-3 text-[10px] font-mono text-text-secondary break-all cursor-pointer hover:bg-accent-subtle transition-colors"
                onClick={() => {
                  navigator.clipboard.writeText(pixData.qr_code || "");
                  toast.success(p ? "Código copiado!" : "Code copied!");
                }}
              >
                {(pixData.qr_code || "").slice(0, 120)}...
                <p className="text-accent text-center mt-2 text-caption font-sans">
                  {p ? "Clique para copiar" : "Click to copy"}
                </p>
              </div>
            </div>

            <button
              onClick={() => setPixData(null)}
              className="w-full py-2 rounded-lg border border-border text-body text-text-secondary hover:bg-surface-elevated transition-colors"
            >
              {p ? "Fechar" : "Close"}
            </button>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}
