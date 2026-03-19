import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { ChevronDown } from "lucide-react";

const faqs = [
  {
    q: "How is Bluewave different from Google Drive or Dropbox?",
    a: "Google Drive stores files. Bluewave manages creative assets. That means AI-generated metadata, approval workflows, role-based access, and status tracking — all purpose-built for creative teams. Think of it as the step up from folders to a real creative workflow.",
  },
  {
    q: "Can I migrate my existing assets?",
    a: "Yes. Bulk upload via drag-and-drop. AI will auto-generate captions and hashtags for everything you upload. Most teams are fully migrated in under an hour.",
  },
  {
    q: "Is my data safe? What about multi-tenancy?",
    a: "Each workspace is completely isolated at the database level. Your data is never mixed with other tenants. All connections are encrypted. JWT-based auth with short-lived tokens.",
  },
  {
    q: "What file types do you support?",
    a: "All major image formats (JPG, PNG, GIF, SVG, WebP, TIFF) and video formats (MP4, MOV, AVI, WebM). Up to 50MB per file on the free plan, higher limits on paid plans.",
  },
  {
    q: "Do I need a credit card to start?",
    a: "No. The free plan is genuinely free — no card required, no trial expiration. Upgrade only when you need more storage or approval workflows.",
  },
  {
    q: "Can I use Bluewave with my existing tools?",
    a: "Bluewave works alongside your current stack. API access is available on Pro plans. Integrations with Figma, Slack, and Zapier are on the roadmap.",
  },
];

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section className="py-24 sm:py-32 bg-[#FAFAFA]">
      <div className="max-w-3xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-[#111827] leading-tight">
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
              className="bg-white rounded-xl border border-gray-100 overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between px-6 py-5 text-left"
              >
                <span className="text-base font-semibold text-[#111827] pr-4">
                  {faq.q}
                </span>
                <ChevronDown
                  className={`w-5 h-5 text-[#9CA3AF] shrink-0 transition-transform duration-200 ${
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
                    <p className="px-6 pb-5 text-[#6b7280] leading-relaxed">
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
