import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { Waves, ArrowRight, ShieldCheck, Palette, Type, Image, Sparkles, Layout, Eye, Target, Monitor } from "lucide-react";
import { Link } from "react-router-dom";
import { useGeo } from "../../contexts/GeoContext";

/* ── Animated Compliance Ring ── */
function HeroComplianceRing() {
  const [score, setScore] = useState(0);
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => { setScore(87); setPhase(1); }, 1800);
    const t2 = setTimeout(() => setPhase(2), 2800);
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
      {/* Deep violet glow behind ring */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[320px] h-[320px] rounded-full"
        style={{ background: "radial-gradient(circle, rgba(124,58,237,0.18) 0%, transparent 70%)", filter: "blur(40px)" }} />

      <div className="relative flex flex-col items-center gap-6">
        {/* Ring */}
        <div className="relative" style={{ width: size, height: size }}>
          {/* Outer glow ring */}
          <div className="absolute inset-0 rounded-full"
            style={{ background: "radial-gradient(circle, rgba(124,58,237,0.12) 40%, transparent 70%)", filter: "blur(12px)" }} />
          <svg width={size} height={size} className="-rotate-90">
            <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth={8} />
            {/* Track ring subtle violet tint */}
            <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="rgba(124,58,237,0.08)" strokeWidth={8} />
            <motion.circle
              cx={size/2} cy={size/2} r={radius} fill="none"
              stroke="url(#violetGold)" strokeWidth={8} strokeLinecap="round"
              strokeDasharray={circumference}
              animate={{ strokeDashoffset: circumference - progress }}
              transition={{ duration: 1.4, ease: "easeOut" }}
              style={{ filter: "drop-shadow(0 0 14px rgba(124,58,237,0.6))" }}
            />
            <defs>
              <linearGradient id="violetGold" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#7c3aed" />
                <stop offset="60%" stopColor="#8b5cf6" />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.8" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {phase === 0 ? (
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}>
                <ShieldCheck className="h-10 w-10" style={{ color: "rgba(124,58,237,0.5)" }} strokeWidth={1} />
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
              <d.icon className="h-3 w-3 shrink-0" style={{ color: "rgba(139,92,246,0.6)" }} strokeWidth={1.5} />
              <span className="text-[10px] text-white/40">{d.label}</span>
              <span className={`text-[10px] font-medium ${d.score >= 90 ? "text-emerald-400" : d.score >= 80 ? "text-violet-400" : "text-amber-400"}`}>
                {d.score}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}

/* ── Floating particles — violet/gold mix ── */
function Particles() {
  const colors = [
    "rgba(124,58,237,0.25)",
    "rgba(139,92,246,0.2)",
    "rgba(245,158,11,0.15)",
    "rgba(16,185,129,0.15)",
  ];
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 36 }).map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            width: `${Math.random() * 2.5 + 1}px`,
            height: `${Math.random() * 2.5 + 1}px`,
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            background: colors[i % colors.length],
            animation: `float${i % 3} ${14 + Math.random() * 18}s ease-in-out infinite`,
            animationDelay: `${Math.random() * 8}s`,
            opacity: Math.random() * 0.5 + 0.1,
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
    <section className="relative min-h-screen flex items-center overflow-hidden"
      style={{ background: "linear-gradient(160deg, #06000f 0%, #0d0020 45%, #060010 100%)" }}>

      {/* Ambient gradients — violet dominant */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Primary violet bloom — top left */}
        <div className="absolute w-[900px] h-[900px] rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(124,58,237,0.18) 0%, transparent 60%)",
            top: "-5%", left: "5%",
            filter: "blur(80px)",
            animation: "drift1 22s ease-in-out infinite"
          }} />
        {/* Secondary emerald — bottom right */}
        <div className="absolute w-[600px] h-[600px] rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(16,185,129,0.10) 0%, transparent 55%)",
            bottom: "5%", right: "8%",
            filter: "blur(100px)",
            animation: "drift2 30s ease-in-out infinite"
          }} />
        {/* Tertiary gold accent — center right */}
        <div className="absolute w-[400px] h-[400px] rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(245,158,11,0.06) 0%, transparent 60%)",
            top: "30%", right: "20%",
            filter: "blur(80px)",
            animation: "drift3 26s ease-in-out infinite"
          }} />
        {/* Subtle horizontal separator line */}
        <div className="absolute bottom-0 left-0 right-0 h-px"
          style={{ background: "linear-gradient(90deg, transparent, rgba(124,58,237,0.15), transparent)" }} />
      </div>

      <Particles />

      <style>{`
        @keyframes drift1 { 0%, 100% { transform: translate(0, 0); } 33% { transform: translate(2%, -3%); } 66% { transform: translate(-3%, 2%); } }
        @keyframes drift2 { 0%, 100% { transform: translate(0, 0); } 33% { transform: translate(-3%, 2%); } 66% { transform: translate(3%, -2%); } }
        @keyframes drift3 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(-2%, -3%); } }
        @keyframes float0 { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(-25px) translateX(8px); } }
        @keyframes float1 { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(18px) translateX(-12px); } }
        @keyframes float2 { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(-12px) translateX(-6px); } }
        @keyframes shimmer { 0% { background-position: 200% center; } 100% { background-position: -200% center; } }
        @keyframes pulseGold { 0%, 100% { opacity: 0.6; } 50% { opacity: 1; } }
      `}</style>

      {/* Nav */}
      <nav className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-5 sm:px-10 py-5">
        {/* Subtle nav blur bar */}
        <div className="absolute inset-0 backdrop-blur-[2px]"
          style={{ background: "linear-gradient(180deg, rgba(6,0,15,0.6) 0%, transparent 100%)" }} />
        <Link to="/" className="relative flex items-center gap-2.5">
          <div className="relative">
            <Waves className="w-5 h-5 drop-shadow-[0_0_10px_rgba(124,58,237,0.8)]"
              style={{ color: "#8b5cf6" }} />
          </div>
          <span className="text-base font-extrabold tracking-tight bg-clip-text text-transparent"
            style={{
              backgroundImage: "linear-gradient(90deg, #a78bfa, #c4b5fd, #a78bfa)",
              backgroundSize: "200% auto",
              animation: "shimmer 3s linear infinite"
            }}>
            Bluewave
          </span>
        </Link>
        <div className="relative flex items-center gap-3">
          {isAuthenticated ? null : (
            <>
              <Link to="/login"
                className="hidden sm:inline-flex px-3 py-2 text-sm text-white/50 hover:text-white transition-colors">
                {t.signIn}
              </Link>
              <Link to="/register"
                className="px-4 py-2 rounded-lg text-white text-sm font-semibold transition-all hover:shadow-[0_0_24px_rgba(124,58,237,0.4)]"
                style={{ background: "linear-gradient(135deg, #7c3aed, #6d28d9)" }}>
                {t.cta}
              </Link>
            </>
          )}
        </div>
      </nav>

      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-5 sm:px-10 w-full grid lg:grid-cols-2 gap-12 lg:gap-20 items-center pt-28 sm:pt-20">

        {/* Left — Copy */}
        <div>
          {/* Eyebrow label */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 rounded-full border"
            style={{
              borderColor: "rgba(124,58,237,0.25)",
              background: "rgba(124,58,237,0.06)",
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400" style={{ animation: "pulseGold 2s ease-in-out infinite" }} />
            <span className="text-[11px] font-semibold text-violet-300/80 tracking-wider uppercase">
              Psychometric Brand Intelligence
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-4xl sm:text-5xl lg:text-[3.6rem] font-bold text-white leading-[1.08] tracking-tight"
          >
            {t.heroHeadline1}
            <br />
            <span className="bg-clip-text text-transparent"
              style={{
                backgroundImage: "linear-gradient(90deg, #a78bfa, #c4b5fd, #f59e0b, #a78bfa)",
                backgroundSize: "200% auto",
                animation: "shimmer 5s linear infinite"
              }}>
              {t.heroHeadline2}
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="mt-6 text-lg text-white/45 max-w-lg leading-relaxed"
          >
            {t.heroSub}
          </motion.p>

          {geo.regionalData?.stat && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="mt-3 text-sm"
              style={{ color: "rgba(167,139,250,0.6)" }}
            >
              {geo.regionalData.stat}
            </motion.p>
          )}

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.25 }}
            className="mt-9 flex flex-col sm:flex-row gap-3"
          >
            {isAuthenticated ? (
              <Link to="/assets"
                className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl text-white font-semibold text-base transition-all hover:shadow-[0_0_36px_rgba(124,58,237,0.45)]"
                style={{ background: "linear-gradient(135deg, #7c3aed, #6d28d9)" }}>
                {t.ctaDashboard} <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <>
                <Link to="/register"
                  className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl text-white font-semibold text-base transition-all hover:shadow-[0_0_36px_rgba(124,58,237,0.45)] group"
                  style={{ background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
                  {t.cta}
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </Link>
                <a href="#features"
                  className="inline-flex items-center justify-center px-7 py-3.5 rounded-xl font-medium text-base transition-all hover:bg-white/[0.06]"
                  style={{
                    border: "1px solid rgba(255,255,255,0.08)",
                    color: "rgba(255,255,255,0.6)"
                  }}>
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
              { text: t.credentialTools, color: "rgba(167,139,250,0.5)" },
              { text: t.credentialAgents, color: "rgba(16,185,129,0.5)" },
              { text: t.credentialBrand, color: "rgba(245,158,11,0.5)" },
            ].filter(i => i.text).map((item) => (
              <span key={item.text} className="text-[11px] font-medium tracking-wide"
                style={{ color: item.color }}>
                {item.text}
              </span>
            ))}
          </motion.div>
        </div>

        {/* Right — Product card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="flex justify-center lg:justify-end"
        >
          {/* Outer glow wrapper */}
          <div className="relative">
            <div className="absolute -inset-px rounded-2xl"
              style={{
                background: "linear-gradient(135deg, rgba(124,58,237,0.3) 0%, rgba(245,158,11,0.1) 50%, rgba(16,185,129,0.1) 100%)",
                filter: "blur(1px)"
              }} />
            <div className="absolute -inset-6 rounded-3xl"
              style={{
                background: "radial-gradient(ellipse, rgba(124,58,237,0.12) 0%, transparent 70%)",
                filter: "blur(20px)"
              }} />

            {/* Card */}
            <div className="relative rounded-2xl max-w-sm w-full p-8 sm:p-10"
              style={{
                background: "rgba(255,255,255,0.03)",
                backdropFilter: "blur(24px)",
                WebkitBackdropFilter: "blur(24px)",
                border: "1px solid rgba(255,255,255,0.07)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(124,58,237,0.12), inset 0 1px 0 rgba(255,255,255,0.05)"
              }}>

              {/* Inner top gradient strip */}
              <div className="absolute top-0 left-0 right-0 h-px rounded-t-2xl"
                style={{ background: "linear-gradient(90deg, transparent, rgba(139,92,246,0.4), transparent)" }} />

              {/* Card header */}
              <div className="flex items-center gap-2 mb-6">
                <ShieldCheck className="h-4 w-4" style={{ color: "#8b5cf6" }} />
                <span className="text-xs font-semibold tracking-wide" style={{ color: "rgba(167,139,250,0.7)" }}>
                  Brand Guardian
                </span>
                <span className="ml-auto text-[10px] font-mono" style={{ color: "rgba(245,158,11,0.5)" }}>
                  8 dimensions
                </span>
              </div>

              {/* Compliance Ring */}
              <HeroComplianceRing />

              {/* Bottom bar */}
              <div className="mt-6 pt-4 flex items-center justify-between"
                style={{ borderTop: "1px solid rgba(255,255,255,0.04)" }}>
                <span className="text-[10px]" style={{ color: "rgba(255,255,255,0.2)" }}>
                  Powered by Claude Vision + PUT
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"
                    style={{ animation: "pulseGold 1.8s ease-in-out infinite" }} />
                  <span className="text-[10px] font-semibold text-emerald-400/70">LIVE</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

      </div>
    </section>
  );
}
