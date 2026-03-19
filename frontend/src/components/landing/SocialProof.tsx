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
  { value: "3", suffix: " weeks/year", label: "saved per team member on file searching" },
  { value: "40", suffix: "%", label: "faster approval cycles" },
  { value: "51", suffix: "%", label: "of teams stop recreating lost assets" },
  { value: "5", suffix: " min", label: "from signup to first upload" },
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
