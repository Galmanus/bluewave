import { motion } from "framer-motion";
import { ShieldAlert, Clock, Eye } from "lucide-react";
import { useGeo } from "../../contexts/GeoContext";

export default function PainPoints() {
  const { t, geo } = useGeo();

  const cards = [
    { icon: ShieldAlert, title: t.pain1Title, desc: t.pain1Desc, stat: t.pain1Stat },
    { icon: Clock, title: t.pain2Title, desc: t.pain2Desc, stat: t.pain2Stat },
    { icon: Eye, title: t.pain3Title, desc: t.pain3Desc, stat: t.pain3Stat },
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
          <span className="text-sm font-semibold text-red-400/80 uppercase tracking-wider">
            {geo.lang === "pt" ? "O problema" : "The problem"}
          </span>
          <h2 className="mt-3 text-3xl sm:text-4xl font-bold text-white leading-tight">
            {t.painTitle}
          </h2>

          {/* Regional context */}
          {geo.regionalData && (
            <motion.p
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 }}
              className="mt-4 text-sm text-amber-400/70 max-w-xl mx-auto"
            >
              {geo.regionalData.painPoint}
            </motion.p>
          )}
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {cards.map((card, i) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.15 }}
              className="bg-white/[0.03] rounded-xl p-8 border border-white/[0.06] hover:border-white/10 hover:-translate-y-1 transition-all duration-200"
            >
              <div className="w-12 h-12 rounded-lg bg-red-500/10 flex items-center justify-center mb-6">
                <card.icon className="w-6 h-6 text-red-400/80" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">{card.title}</h3>
              <p className="text-[#9CA3AF] leading-relaxed mb-6">{card.desc}</p>
              <p className="text-sm font-medium text-red-400/70 border-t border-white/[0.06] pt-4">{card.stat}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
