import { motion } from "framer-motion";
import { useState } from "react";
import { Check } from "lucide-react";
import { Link } from "react-router-dom";
import { useGeo } from "../../contexts/GeoContext";

const plans = [
  {
    name: "Free",
    monthlyPrice: 0,
    annualPrice: 0,
    description: "Try the Brand Guardian with no commitment",
    features: [
      "Up to 3 users",
      "5 GB storage",
      "50 AI actions/month",
      "Brand compliance checks (8 dimensions)",
      "AI captions + hashtags on upload",
      "Approval workflows",
    ],
    cta: "Start free",
    ctaLink: "/register",
    highlighted: false,
  },
  {
    name: "Pro",
    monthlyPrice: 29,
    annualPrice: 24,
    description: "For teams that ship content daily",
    features: [
      "Unlimited users",
      "100 GB storage",
      "Unlimited AI actions",
      "Brand Content Generator (10 content types)",
      "Social calendar + scheduling",
      "Role-based access (admin / editor / viewer)",
      "API access",
    ],
    cta: "Start free trial",
    ctaLink: "/register",
    highlighted: true,
    badge: "Best value",
  },
  {
    name: "Enterprise",
    monthlyPrice: null,
    annualPrice: null,
    description: "For agencies managing multiple brands",
    features: [
      "Everything in Pro",
      "Unlimited storage",
      "Multi-brand workspaces",
      "Autonomous Wave agent (89 tools, 9 specialists)",
      "Custom integrations",
      "Dedicated support + SLA",
    ],
    cta: "Contact us",
    ctaLink: "mailto:m.galmanus@gmail.com",
    highlighted: false,
  },
];

interface PricingProps {
  isAuthenticated?: boolean;
}

export default function Pricing({ isAuthenticated }: PricingProps) {
  const { t } = useGeo();
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
            Monthly
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
            Annual
            <span className="ml-1.5 text-xs text-emerald-600 font-semibold">
              Save 20%
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
                      ${annual ? plan.annualPrice : plan.monthlyPrice}
                    </span>
                    <span className="text-white/50">
                      {plan.monthlyPrice === 0
                        ? "/month"
                        : `/user/month`}
                    </span>
                    {annual && plan.monthlyPrice > 0 && (
                      <p className="text-xs text-[#9CA3AF] mt-1">
                        billed annually
                      </p>
                    )}
                  </>
                ) : (
                  <span className="text-4xl font-bold text-white">
                    Custom
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
