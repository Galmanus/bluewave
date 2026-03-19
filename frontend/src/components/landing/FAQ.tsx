import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { ChevronDown } from "lucide-react";

const faqs = [
  {
    q: "What does the Brand Guardian actually check?",
    a: "8 dimensions: color accuracy (with Delta-E measurement), typography, logo presence, tone of voice, composition, photography style, strategic coherence, and channel adequacy. Each dimension is scored 0-100 with a weighted total and specific fix recommendations.",
  },
  {
    q: "How is this different from a regular DAM tool?",
    a: "Regular DAMs store files. Bluewave has an autonomous AI agent that analyzes every asset against your brand DNA, generates on-brand content, and enforces compliance automatically. The agent has 89 tools and 9 specialist sub-agents — it doesn't just store your assets, it governs them.",
  },
  {
    q: "Can I upload my brand guidelines?",
    a: "Yes. Define your colors (hex codes), fonts, tone of voice, do's and don'ts, and custom rules. The agent uses these as the baseline for every compliance check. Changes to guidelines apply to all future checks immediately.",
  },
  {
    q: "What content can the agent generate?",
    a: "Captions, stories, headlines, CTAs, product descriptions, ad copy, email sequences, hashtag strategies, social calendars, and competitor audits — all on-brand, in 7 channels, in any language.",
  },
  {
    q: "Do I need technical knowledge to use it?",
    a: "No. Upload an image, get a compliance report. Type a prompt, get on-brand content. The dashboard is designed for creative teams, not engineers.",
  },
  {
    q: "Do I need a credit card to start?",
    a: "No. The free plan is genuinely free — no card required, no trial expiration.",
  },
];

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section className="py-24 sm:py-32 bg-[#0a0a1a]">
      <div className="max-w-3xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-white leading-tight">
            Frequently asked questions
          </h2>
        </motion.div>

        <div className="space-y-3">
          {faqs.map((faq, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.08 }}
              className="bg-white/[0.03] rounded-xl border border-white/[0.06] overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between px-6 py-5 text-left"
              >
                <span className="text-base font-semibold text-white pr-4">
                  {faq.q}
                </span>
                <ChevronDown
                  className={`w-5 h-5 text-white/40 shrink-0 transition-transform duration-200 ${
                    open === i ? "rotate-180" : ""
                  }`}
                />
              </button>
              <AnimatePresence>
                {open === i && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="px-6 pb-5 text-[#9CA3AF] leading-relaxed">
                      {faq.a}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
