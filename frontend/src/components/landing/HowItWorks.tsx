import { motion } from "framer-motion";
import { Rocket, CloudUpload, Send, ShieldCheck } from "lucide-react";

const steps = [
  {
    icon: Rocket,
    title: "Create your workspace",
    description:
      "Sign up, name your team, invite your first members. No credit card required.",
  },
  {
    icon: CloudUpload,
    title: "Upload your assets",
    description:
      "Drag and drop images and videos. AI automatically generates captions, hashtags, and metadata.",
  },
  {
    icon: Send,
    title: "Submit for review",
    description:
      "When an asset is ready, submit it for approval. Admins review and approve or reject with feedback.",
  },
  {
    icon: ShieldCheck,
    title: "Ship with confidence",
    description:
      "Approved assets are clearly marked. No more guessing which version is final.",
  },
];

export default function HowItWorks() {
  return (
    <section className="py-24 sm:py-32 bg-white">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-[#111827] leading-tight">
            Up and running in 5 minutes
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 relative">
          {/* Connecting line (desktop only) */}
          <div className="hidden lg:block absolute top-10 left-[12.5%] right-[12.5%] h-px bg-gray-200" />

          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.15 }}
              className="relative text-center"
            >
              <div className="relative z-10 w-20 h-20 rounded-full bg-blue-50 flex items-center justify-center mx-auto mb-6">
                <span className="absolute -top-1 -right-1 w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
                  {i + 1}
                </span>
                <step.icon className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-[#111827] mb-2">
                {step.title}
              </h3>
              <p className="text-sm text-[#6b7280] leading-relaxed max-w-xs mx-auto">
                {step.description}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Mid-page CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="text-center mt-16"
        >
          <a
            href="/register"
            className="inline-flex items-center px-8 py-3.5 rounded-lg bg-blue-600 text-white font-semibold text-lg hover:bg-blue-700 transition-all duration-150 hover:scale-[1.02] hover:shadow-[0_0_24px_rgba(37,99,235,0.4)]"
          >
            Start free — no credit card required
          </a>
        </motion.div>
      </div>
    </section>
  );
}
