import { motion, useInView } from "framer-motion";
import { useRef, useEffect, useState } from "react";
import { Quote } from "lucide-react";

function CountUp({ target, suffix = "" }: { target: string; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true });
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    if (!isInView) return;

    const numericMatch = target.match(/[\d.]+/);
    if (!numericMatch) {
      setDisplay(target);
      return;
    }

    const end = parseFloat(numericMatch[0]);
    const prefix = target.slice(0, target.indexOf(numericMatch[0]));
    const isDecimal = target.includes(".");
    const duration = 1200;
    const start = performance.now();

    function animate(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = end * eased;
      setDisplay(
        prefix + (isDecimal ? current.toFixed(0) : Math.round(current).toString())
      );
      if (progress < 1) requestAnimationFrame(animate);
    }

    requestAnimationFrame(animate);
  }, [isInView, target]);

  return (
    <span ref={ref}>
      {display}
      {suffix}
    </span>
  );
}

const metrics = [
  { value: "58", suffix: " tools", label: "operational skills across 13 modules" },
  { value: "6", suffix: " agents", label: "PhD-level specialists coordinated by Wave" },
  { value: "99", suffix: "%", label: "cheaper billing vs Stripe (on Hedera)" },
  { value: "1", suffix: " session", label: "from zero to autonomous agent" },
];

const testimonials = [
  {
    quote:
      "We went from 'where's that file?' 10 times a day to zero. Bluewave replaced our entire Dropbox + email review workflow in one afternoon.",
    name: "Rachel Torres",
    title: "Creative Director",
    company: "Spark Agency",
  },
  {
    quote:
      "The AI captions alone save us 4 hours a week. We used to manually write alt text and hashtags for every single asset.",
    name: "David Chen",
    title: "Content Manager",
    company: "Meridian Brands",
  },
  {
    quote:
      "Our approval process was a 5-day email chain. Now it's same-day. The status badges alone changed everything.",
    name: "Lisa Okafor",
    title: "Marketing VP",
    company: "NovaCraft Studios",
  },
];

export default function SocialProof() {
  return (
    <section className="py-24 sm:py-32 bg-[#111827]">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-sm font-semibold text-blue-400 uppercase tracking-wider">
            By the numbers
          </span>
        </motion.div>

        {/* Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 mb-20">
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.1 }}
              className="text-center"
            >
              <div className="text-4xl sm:text-5xl font-bold text-white mb-2">
                {m.value === "5" && "< "}
                <CountUp target={m.value} suffix={m.suffix} />
              </div>
              <p className="text-sm text-[#9CA3AF]">{m.label}</p>
            </motion.div>
          ))}
        </div>

        {/* Live Agent Banner */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mb-20"
        >
          <a
            href="https://www.moltbook.com/u/bluewaveprime"
            target="_blank"
            rel="noopener noreferrer"
            className="block bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-blue-500/20 rounded-xl p-8 hover:border-blue-500/40 transition-colors"
          >
            <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 shrink-0">
                  <span className="text-2xl">🌊</span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">
                    Wave is live on Moltbook
                  </h3>
                  <p className="text-[#9CA3AF] mt-1">
                    Our autonomous agent operates 24/7 on the AI social network — posting, learning, engaging with other agents in real-time.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-6 text-center shrink-0">
                <div>
                  <div className="text-2xl font-bold text-white">@bluewaveprime</div>
                  <div className="text-xs text-blue-400 mt-1">View live profile →</div>
                </div>
              </div>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              {["Self-evolving skills", "Persistent memory", "Multi-agent orchestration", "Computer vision", "Sales prospecting", "Hedera micropayments"].map(tag => (
                <span key={tag} className="px-3 py-1 rounded-full text-xs font-medium bg-white/5 text-white/60 border border-white/10">
                  {tag}
                </span>
              ))}
            </div>
          </a>
        </motion.div>

        {/* Testimonials */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {testimonials.map((t, i) => (
            <motion.div
              key={t.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.2 + i * 0.15 }}
              className="bg-white/5 border border-white/10 rounded-xl p-8 relative"
            >
              <Quote className="w-8 h-8 text-blue-500/20 absolute top-6 right-6" />
              <p className="text-[#F9FAFB] leading-relaxed mb-6">
                "{t.quote}"
              </p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-600/20 flex items-center justify-center text-sm font-bold text-blue-400">
                  {t.name.charAt(0)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-[#F9FAFB]">
                    {t.name}
                  </p>
                  <p className="text-xs text-[#9CA3AF]">
                    {t.title}, {t.company}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
