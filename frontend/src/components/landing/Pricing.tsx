import { motion } from "framer-motion";
import { useState } from "react";
import { Check } from "lucide-react";
import { Link } from "react-router-dom";
import { useGeo } from "../../contexts/GeoContext";

function getPlans(p: boolean) {
  // BRL conversion: ~5.5x USD. Rounded to clean numbers.
  return [
    {
      name: p ? "Grátis" : "Free",
      monthlyPrice: 0,
      annualPrice: 0,
      currency: p ? "R$" : "$",
      description: p ? "Teste o Brand Guardian sem compromisso" : "Try the Brand Guardian with no commitment",
      features: p ? [
        "Até 3 usuários",
        "5 GB de armazenamento",
        "50 ações de IA/mês",
        "Compliance de marca (8 dimensões)",
        "Captions + hashtags automáticos",
        "Workflows de aprovação",
      ] : [
        "Up to 3 users",
        "5 GB storage",
        "50 AI actions/month",
        "Brand compliance checks (8 dimensions)",
        "AI captions + hashtags on upload",
        "Approval workflows",
      ],
      cta: p ? "Começar grátis" : "Start free",
      ctaLink: "/register",
      highlighted: false,
    },
    {
      name: "Pro",
      monthlyPrice: p ? 149 : 29,
      annualPrice: p ? 119 : 24,
      currency: p ? "R$" : "$",
      description: p ? "Para equipes que publicam conteúdo diariamente" : "For teams that ship content daily",
      features: p ? [
        "Usuários ilimitados",
        "100 GB de armazenamento",
        "Ações de IA ilimitadas",
        "Gerador de Conteúdo (10 tipos)",
        "Calendário social + agendamento",
        "Acesso por função (admin / editor / viewer)",
        "Acesso à API",
      ] : [
        "Unlimited users",
        "100 GB storage",
        "Unlimited AI actions",
        "Brand Content Generator (10 content types)",
        "Social calendar + scheduling",
        "Role-based access (admin / editor / viewer)",
        "API access",
      ],
      cta: p ? "Teste grátis" : "Start free trial",
      ctaLink: "/register",
      highlighted: true,
      badge: p ? "Melhor custo-benefício" : "Best value",
    },
    {
      name: "Enterprise",
      monthlyPrice: null,
      annualPrice: null,
      currency: p ? "R$" : "$",
      description: p ? "Para agências com múltiplas marcas" : "For agencies managing multiple brands",
      features: p ? [
        "Tudo do Pro",
        "Armazenamento ilimitado",
        "Workspaces multi-marca",
        "Agente Wave autônomo (89 tools, 9 especialistas)",
        "Integrações customizadas",
        "Suporte dedicado + SLA",
      ] : [
        "Everything in Pro",
        "Unlimited storage",
        "Multi-brand workspaces",
        "Autonomous Wave agent (89 tools, 9 specialists)",
        "Custom integrations",
        "Dedicated support + SLA",
      ],
      cta: p ? "Fale conosco" : "Contact us",
      ctaLink: "mailto:m.galmanus@gmail.com",
      highlighted: false,
    },
  ];
}

interface PricingProps {
  isAuthenticated?: boolean;
}

export default function Pricing({ isAuthenticated }: PricingProps) {
  const { t, geo } = useGeo();
  const p = geo.lang === "pt";
  const plans = getPlans(p);
  const [annual, setAnnual] = useState(true);

  return (
    <section id="pricing" className="py-24 sm:py-32 bg-[#111827]">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <span className="text-sm font-semibold text-blue-400 uppercase tracking-wider">
            {t.pricingEyebrow}
          </span>
          <h2 className="mt-3 text-3xl sm:text-4xl font-bold text-white leading-tight">
            {t.pricingTitle}
          </h2>
          <p className="mt-4 text-lg text-white/50">
            {t.pricingSub}
          </p>
        </motion.div>

        {/* Billing toggle */}
        <div className="flex items-center justify-center gap-3 mb-12">
          <span
            className={`text-sm font-medium ${
              !annual ? "text-white" : "text-[#9CA3AF]"
            }`}
          >
            {t.pricingMonthly}
          </span>
          <button
            onClick={() => setAnnual(!annual)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              annual ? "bg-blue-600" : "bg-white/20"
            }`}
          >
            <div
              className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                annual ? "translate-x-6" : "translate-x-0.5"
              }`}
            />
          </button>
          <span
            className={`text-sm font-medium ${
              annual ? "text-white" : "text-[#9CA3AF]"
            }`}
          >
            {t.pricingAnnual}
            <span className="ml-1.5 text-xs text-emerald-600 font-semibold">
              {t.pricingSave}
            </span>
          </span>
        </div>

        {/* Plans */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.15 }}
              className={`relative rounded-xl p-8 ${
                plan.highlighted
                  ? "bg-white/[0.06] border-2 border-blue-500/50 shadow-lg shadow-blue-500/10 scale-[1.02]"
                  : "bg-white/[0.03] border border-white/[0.06]"
              }`}
            >
              {plan.badge && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-semibold bg-blue-600 text-white">
                  {plan.badge}
                </span>
              )}

              <h3 className="text-xl font-bold text-white mb-2">
                {plan.name}
              </h3>
              <p className="text-sm text-white/50 mb-6">{plan.description}</p>

              <div className="mb-8">
                {plan.monthlyPrice !== null ? (
                  <>
                    <span className="text-4xl font-bold text-white">
                      {plan.currency}{annual ? plan.annualPrice : plan.monthlyPrice}
                    </span>
                    <span className="text-white/50">
                      {plan.monthlyPrice === 0
                        ? t.pricingPerMonth
                        : t.pricingPerUser}
                    </span>
                    {annual && plan.monthlyPrice > 0 && (
                      <p className="text-xs text-[#9CA3AF] mt-1">
                        {t.pricingBilled}
                      </p>
                    )}
                  </>
                ) : (
                  <span className="text-4xl font-bold text-white">
                    {t.pricingCustom}
                  </span>
                )}
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                    <span className="text-sm text-white/70">{f}</span>
                  </li>
                ))}
              </ul>

              <Link
                to={isAuthenticated ? "/assets" : plan.ctaLink}
                className={`block text-center px-6 py-3 rounded-lg font-semibold transition-all duration-150 ${
                  plan.highlighted
                    ? "bg-blue-600 text-white hover:bg-blue-700 hover:scale-[1.02] hover:shadow-[0_0_24px_rgba(37,99,235,0.3)]"
                    : "bg-white/10 text-white hover:bg-white/20"
                }`}
              >
                {isAuthenticated ? "Go to Dashboard" : plan.cta}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
