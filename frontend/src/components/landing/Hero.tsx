import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { Waves, ArrowRight, ShieldCheck, Palette, Type, Image, Sparkles, Layout, Eye, Target, Monitor } from "lucide-react";
import { Link } from "react-router-dom";
import { useGeo } from "../../contexts/GeoContext";

/* ── Animated Compliance Ring (the hero visual) ── */
function HeroComplianceRing() {
  const [score, setScore] = useState(0);
  const [phase, setPhase] = useState(0); // 0=scanning, 1=scored, 2=dimensions

  useEffect(() => {
    // Phase 0: scanning animation
    const t1 = setTimeout(() => { setScore(87); setPhase(1); }, 1800);
    // Phase 2: show dimensions
    const t2 = setTimeout(() => setPhase(2), 2800);
    // Reset cycle
    const t3 = setTimeout(() => { setScore(0); setPhase(0); }, 9000);
    const loop = setInterval(() => {
      setScore(0); setPhase(0);
      setTimeout(() => { setScore(87); setPhase(1); }, 1800);
      setTimeout(() => setPhase(2), 2800);
    }, 9000);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearInterval(loop); };
  }, []);

  const size = 200;
  const radius = (size - 14) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  const dimensions = [
    { icon: Palette, label: "Cores", score: 92 },
    { icon: Type, label: "Tipografia", score: 78 },
    { icon: Image, label: "Logo", score: 95 },
    { icon: Sparkles, label: "Tom", score: 88 },
    { icon: Layout, label: "Composição", score: 82 },
    { icon: Eye, label: "Fotografia", score: 90 },
    { icon: Target, label: "Estratégia", score: 85 },
    { icon: Monitor, label: "Canal", score: 88 },
  ];

  return (
    <div className="relative">
      {/* Glow behind ring */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] rounded-full bg-cyan-500/10 blur-[80px]" />

      <div className="relative flex flex-col items-center gap-6">
        {/* Ring */}
        <div className="relative" style={{ width: size, height: size }}>
          <svg width={size} height={size} className="-rotate-90">
            <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth={8} />
            <motion.circle
              cx={size/2} cy={size/2} r={radius} fill="none"
              stroke="#06b6d4" strokeWidth={8} strokeLinecap="round"
              strokeDasharray={circumference}
              animate={{ strokeDashoffset: circumference - progress }}
              transition={{ duration: 1.2, ease: "easeOut" }}
              style={{ filter: "drop-shadow(0 0 12px rgba(6,182,212,0.4))" }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {phase === 0 ? (
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}>
                <ShieldCheck className="h-10 w-10 text-cyan-400/50" strokeWidth={1} />
              </motion.div>
            ) : (
              <motion.div initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="text-center">
                <span className="text-5xl font-bold text-white">{score}</span>
                <span className="text-lg text-white/30">/100</span>
              </motion.div>
            )}
          </div>
        </div>

        {/* 8 Dimensions */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: phase >= 2 ? 1 : 0, y: phase >= 2 ? 0 : 10 }}
          transition={{ duration: 0.5 }}
          className="grid grid-cols-4 gap-x-4 gap-y-2"
        >
          {dimensions.map((d, i) => (
            <motion.div
              key={d.label}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: phase >= 2 ? 1 : 0, x: phase >= 2 ? 0 : -5 }}
              transition={{ delay: i * 0.06, duration: 0.3 }}
              className="flex items-center gap-1.5"
            >
              <d.icon className="h-3 w-3 text-cyan-400/50" strokeWidth={1.5} />
              <span className="text-[10px] text-white/40">{d.label}</span>
              <span className={`text-[10px] font-medium ${d.score >= 90 ? "text-emerald-400" : d.score >= 80 ? "text-cyan-400" : "text-amber-400"}`}>
                {d.score}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}

/* ── Floating particles ── */
function Particles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 30 }).map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full bg-cyan-400/20"
          style={{
            width: `${Math.random() * 2 + 1}px`,
            height: `${Math.random() * 2 + 1}px`,
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            animation: `float${i % 3} ${14 + Math.random() * 18}s ease-in-out infinite`,
            animationDelay: `${Math.random() * 8}s`,
            opacity: Math.random() * 0.4 + 0.1,
          }}
        />
      ))}
    </div>
  );
}

interface HeroProps { isAuthenticated?: boolean; }

export default function Hero({ isAuthenticated }: HeroProps) {
  const { t, geo } = useGeo();

  return (
    <section className="relative min-h-screen flex items-center overflow-hidden bg-gradient-to-b from-[#040810] via-[#060d16] to-[#0a1420]">
      {/* Ambient gradients */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute w-[800px] h-[800px] rounded-full blur-[200px] opacity-15"
          style={{ background: "radial-gradient(circle, rgba(6,182,212,0.3) 0%, transparent 60%)", top: "10%", left: "15%", animation: "drift1 22s ease-in-out infinite" }} />
        <div className="absolute w-[600px] h-[600px] rounded-full blur-[180px] opacity-10"
          style={{ background: "radial-gradient(circle, rgba(8,145,178,0.25) 0%, transparent 55%)", bottom: "10%", right: "10%", animation: "drift2 28s ease-in-out infinite" }} />
      </div>

      <Particles />

      <style>{`
        @keyframes drift1 { 0%, 100% { transform: translate(0, 0); } 33% { transform: translate(3%, -2%); } 66% { transform: translate(-2%, 3%); } }
        @keyframes drift2 { 0%, 100% { transform: translate(0, 0); } 33% { transform: translate(-4%, 2%); } 66% { transform: translate(2%, -3%); } }
        @keyframes float0 { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(-25px) translateX(8px); } }
        @keyframes float1 { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(18px) translateX(-12px); } }
        @keyframes float2 { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(-12px) translateX(-6px); } }
        @keyframes shimmer { 0% { background-position: 200% center; } 100% { background-position: -200% center; } }
      `}</style>

      {/* Nav */}
      <nav className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-5 sm:px-10 py-5">
        <Link to="/" className="flex items-center gap-2">
          <Waves className="w-5 h-5 text-cyan-400 drop-shadow-[0_0_8px_rgba(6,182,212,0.6)]" />
          <span className="text-base font-extrabold tracking-tight bg-gradient-to-r from-cyan-300 via-teal-400 to-cyan-300 bg-clip-text text-transparent" style={{backgroundSize: '200% auto', animation: 'shimmer 3s linear infinite'}}>Bluewave</span>
        </Link>
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <Link to="/assets" className="px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-700 transition-all inline-flex items-center gap-1.5">
              {t.ctaDashboard} <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <>
              <Link to="/login" className="hidden sm:inline-flex px-3 py-2 text-sm text-white/60 hover:text-white transition-colors">{t.signIn}</Link>
              <Link to="/register" className="px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-700 transition-all">{t.cta}</Link>
            </>
          )}
        </div>
      </nav>

      {/* Content — 2 column: copy left, product right */}
      <div className="relative z-10 max-w-7xl mx-auto px-5 sm:px-10 w-full grid lg:grid-cols-2 gap-12 lg:gap-16 items-center pt-28 sm:pt-20">

        {/* Left — Copy */}
        <div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-4xl sm:text-5xl lg:text-[3.5rem] font-bold text-white leading-[1.1] tracking-tight"
          >
            {t.heroHeadline1}
            <br />
            <span className="bg-gradient-to-r from-cyan-300 via-teal-400 to-cyan-300 bg-clip-text text-transparent" style={{backgroundSize: '200% auto', animation: 'shimmer 4s linear infinite'}}>
              {t.heroHeadline2}
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="mt-5 text-lg text-white/50 max-w-lg leading-relaxed"
          >
            {t.heroSub}
          </motion.p>

          {/* Regional context — only show if stat is non-empty */}
          {geo.regionalData?.stat && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="mt-3 text-sm text-cyan-400/60"
            >
              {geo.regionalData.stat}
            </motion.p>
          )}

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.25 }}
            className="mt-8 flex flex-col sm:flex-row gap-3"
          >
            {isAuthenticated ? (
              <Link to="/assets" className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-cyan-600 text-white font-semibold text-base hover:bg-cyan-700 transition-all hover:shadow-[0_0_30px_rgba(6,182,212,0.3)]">
                {t.ctaDashboard} <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <>
                <Link to="/register" className="inline-flex items-center justify-center px-7 py-3.5 rounded-xl bg-cyan-600 text-white font-semibold text-base hover:bg-cyan-700 transition-all hover:shadow-[0_0_30px_rgba(6,182,212,0.3)]">
                  {t.cta}
                </Link>
                <a href="#features" className="inline-flex items-center justify-center px-7 py-3.5 rounded-xl border border-white/10 text-white/70 font-medium text-base hover:bg-white/5 transition-all">
                  {t.ctaDemo}
                </a>
              </>
            )}
          </motion.div>

          {/* Credentials */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-10 flex flex-wrap gap-x-6 gap-y-2"
          >
            {[
              { text: t.credentialTools, color: "text-cyan-500/50" },
              { text: t.credentialAgents, color: "text-teal-500/50" },
              { text: t.credentialBrand, color: "text-amber-500/50" },
            ].map((item) => (
              <span key={item.text} className={`text-[11px] font-medium ${item.color} tracking-wide`}>
                {item.text}
              </span>
            ))}
          </motion.div>
        </div>

        {/* Right — Product in action */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="flex justify-center lg:justify-end"
        >
          <div className="relative rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm p-8 sm:p-10 max-w-sm w-full">
            {/* Card header */}
            <div className="flex items-center gap-2 mb-6">
              <ShieldCheck className="h-4 w-4 text-cyan-400" />
              <span className="text-xs font-medium text-white/50">Brand Guardian</span>
              <span className="ml-auto text-[10px] text-cyan-400/40 font-mono">8 dimensions</span>
            </div>

            {/* Compliance Ring */}
            <HeroComplianceRing />

            {/* Bottom bar */}
            <div className="mt-6 pt-4 border-t border-white/[0.04] flex items-center justify-between">
              <span className="text-[10px] text-white/20">Powered by Claude Vision + PUT</span>
              <span className="text-[10px] text-emerald-400/50 font-medium">LIVE</span>
            </div>
          </div>
        </motion.div>

      </div>
    </section>
  );
}
