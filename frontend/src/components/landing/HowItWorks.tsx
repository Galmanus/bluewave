import { motion } from "framer-motion";
import { Upload, Shield, Sparkles, CheckCircle2 } from "lucide-react";
import { useGeo } from "../../contexts/GeoContext";

export default function HowItWorks() {
  const { t } = useGeo();

  const steps = [
    { icon: Upload, title: t.how1, description: t.how1d },
    { icon: Sparkles, title: t.how2, description: t.how2d },
    { icon: Shield, title: t.how3, description: t.how3d },
    { icon: CheckCircle2, title: t.how4, description: t.how4d },
  ];
  return (
    <section className="py-24 sm:py-32 bg-[#0d1117]">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-white leading-tight">
            {t.howTitle}
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 relative">
          <div className="hidden lg:block absolute top-10 left-[12.5%] right-[12.5%] h-px bg-white/10" />

          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.15 }}
              className="relative text-center"
            >
              <div className="relative z-10 w-20 h-20 rounded-full bg-blue-500/10 flex items-center justify-center mx-auto mb-6">
                <span className="absolute -top-1 -right-1 w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
                  {i + 1}
                </span>
                <step.icon className="w-8 h-8 text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                {step.title}
              </h3>
              <p className="text-sm text-[#9CA3AF] leading-relaxed max-w-xs mx-auto">
                {step.description}
              </p>
            </motion.div>
          ))}
        </div>

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
            {t.howCta}
          </a>
        </motion.div>
      </div>
    </section>
  );
}
