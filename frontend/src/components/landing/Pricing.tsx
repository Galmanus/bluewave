import { motion } from "framer-motion";
import { useState } from "react";
import { Check } from "lucide-react";
import { Link } from "react-router-dom";
import { useGeo } from "../../contexts/GeoContext";

function getPlans(p: boolean) {
  return [
    {
      name: p ? "Grátis" : "Free",
      monthlyPrice: 0,
      annualPrice: 0,
      currency: p ? "R$" : "$",
      description: p ? "Teste o Brand Guardian sem compromisso" : "Try the Brand Guardian — no commitment",
      features: p ? [
        "1 marca",
        "50 checks de compliance/mês",
        "Captions + hashtags automáticos",
        "Análise em 8 dimensões",
        "Workflows de aprovação",
      ] : [
        "1 brand",
        "50 compliance checks/month",
        "AI captions + hashtags",
        "8-dimension analysis",
        "Approval workflows",
      ],
      cta: p ? "Começar grátis" : "Start free",
      ctaLink: "/register",
      highlighted: false,
    },
    {
      name: "Pro",
      monthlyPrice: p ? 197 : 39,
      annualPrice: p ? 157 : 29,
      currency: p ? "R$" : "$",
      description: p ? "Para equipes e freelancers que publicam diariamente" : "For teams that ship content daily",
      features: p ? [
        "3 marcas",
        "Checks de compliance ilimitados",
        "Gerador de conteúdo (10 tipos, 7 canais)",
        "Certificado de conformidade por asset",
        "Calendário social + agendamento",
        "Acesso à API",
      ] : [
        "3 brands",
        "Unlimited compliance checks",
        "Content generator (10 types, 7 channels)",
        "Compliance certificate per asset",
        "Social calendar + scheduling",
        "API access",
      ],
      cta: p ? "Teste 14 dias grátis" : "14-day free trial",
      ctaLink: "/register",
      highlighted: true,
      badge: p ? "Mais popular" : "Most popular",
    },
    {
      name: p ? "Agência" : "Agency",
      monthlyPrice: p ? 497 : 99,
      annualPrice: p ? 397 : 79,
      currency: p ? "R$" : "$",
      description: p ? "Para agências que atendem múltiplos clientes" : "For agencies managing multiple clients",
      features: p ? [
        "Marcas ilimitadas",
        "Extração de Brand DNA (via IA)",
        "White-label para clientes",
        "R$97/mês por cliente adicional",
        "Agente Wave autônomo (89 tools)",
        "Suporte prioritário",
        "Certificados de compliance ilimitados",
      ] : [
        "Unlimited brands",
        "Brand DNA extraction (AI-powered)",
        "White-label for clients",
        "$19/month per additional client",
        "Autonomous Wave agent (89 tools)",
        "Priority support",
        "Unlimited compliance certificates",
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
          <span className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">
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
              annual ? "bg-cyan-600" : "bg-white/20"
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
                  ? "bg-white/[0.06] border-2 border-cyan-500/50 shadow-lg shadow-blue-500/10 scale-[1.02]"
                  : "bg-white/[0.03] border border-white/[0.06]"
              }`}
            >
              {plan.badge && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-semibold bg-cyan-600 text-white">
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
                    ? "bg-cyan-600 text-white hover:bg-cyan-700 hover:scale-[1.02] hover:shadow-[0_0_24px_rgba(6,182,212,0.3)]"
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
