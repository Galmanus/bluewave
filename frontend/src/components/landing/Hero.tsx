import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { Waves, ArrowRight, Bot, Search, Eye, Shield, BarChart3, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { useGeo } from "../../contexts/GeoContext";

const TERMINAL_LINES = [
  { type: "input", text: "find creative agencies with content ops problems" },
  { type: "status", text: "Searching web + LinkedIn...", icon: "search" },
  { type: "status", text: "Delegating to Strategist...", icon: "agent" },
  { type: "output", text: "Found 5 prospects. Top match:" },
  { type: "result", text: "Yard NYC — 95/100 (AdAge Small Agency of the Year)" },
  { type: "result", text: "CEO: Ruth Bernstein | 96 employees" },
  { type: "status", text: "Generating outreach...", icon: "zap" },
  { type: "output", text: "4-touch sequence ready (email + LinkedIn)" },
  { type: "divider", text: "" },
  { type: "input", text: "check brand compliance on this image" },
  { type: "status", text: "Claude Vision analyzing...", icon: "eye" },
  { type: "result", text: "Compliance: 87/100 — typography off-brand" },
  { type: "result", text: "Fix: Helvetica → Inter (x-height differs 7%)" },
  { type: "divider", text: "" },
  { type: "input", text: "I need a Hacker News monitor" },
  { type: "status", text: "Creating skill...", icon: "zap" },
  { type: "output", text: "hacker_news_monitor.py — 4 new tools created" },
  { type: "result", text: "9KB Python, validated, registered. Live now." },
];

function HeroTerminal() {
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setVisibleLines((prev) => {
        if (prev >= TERMINAL_LINES.length) {
          setTimeout(() => setVisibleLines(0), 3000);
          return prev;
        }
        return prev + 1;
      });
    }, 600);
    return () => clearInterval(timer);
  }, []);

  const iconMap: Record<string, React.ReactNode> = {
    search: <Search className="w-3 h-3" />,
    agent: <Bot className="w-3 h-3" />,
    eye: <Eye className="w-3 h-3" />,
    zap: <Zap className="w-3 h-3" />,
    shield: <Shield className="w-3 h-3" />,
    chain: <BarChart3 className="w-3 h-3" />,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.7 }}
      className="mt-10 sm:mt-16 mx-auto max-w-3xl px-2 sm:px-0"
    >
      <div className="relative rounded-lg sm:rounded-xl border border-white/10 bg-[#0d1117] shadow-2xl shadow-blue-500/5 overflow-hidden">
        <div className="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 sm:py-3 bg-[#161b22] border-b border-white/5">
          <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-red-500/70" />
          <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-yellow-500/70" />
          <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-green-500/70" />
          <div className="ml-2 sm:ml-3 flex items-center gap-1.5 sm:gap-2 flex-1 min-w-0">
            <Bot className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-cyan-400 shrink-0" />
            <span className="text-[10px] sm:text-xs text-white/40 font-mono truncate">wave@bluewave</span>
            <span className="text-[9px] sm:text-[10px] text-green-400/60 ml-auto font-mono shrink-0 hidden sm:inline">89 tools active</span>
          </div>
        </div>

        <div className="p-3 sm:p-5 font-mono text-[10px] sm:text-[13px] leading-relaxed h-[280px] sm:h-[340px] overflow-hidden">
          {TERMINAL_LINES.slice(0, visibleLines).map((line, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className={`${line.type === "divider" ? "my-3 border-t border-white/5" : "mb-1"}`}
            >
              {line.type === "input" && (
                <div className="flex items-start gap-2">
                  <span className="text-cyan-400 shrink-0">{">"}</span>
                  <span className="text-white/90">{line.text}</span>
                </div>
              )}
              {line.type === "status" && (
                <div className="flex items-center gap-2 text-yellow-400/70">
                  {line.icon && iconMap[line.icon]}
                  <span>{line.text}</span>
                </div>
              )}
              {line.type === "output" && (
                <div className="text-green-400/90 mt-1">{line.text}</div>
              )}
              {line.type === "result" && (
                <div className="text-white/60 pl-4">{line.text}</div>
              )}
            </motion.div>
          ))}
          {visibleLines < TERMINAL_LINES.length && (
            <span className="inline-block w-2 h-4 bg-cyan-400/80 animate-pulse" />
          )}
        </div>

        <div className="px-3 sm:px-4 py-2 bg-[#161b22] border-t border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2 sm:gap-4 flex-wrap">
            {[
              { label: "9 agents", color: "text-blue-400" },
              { label: "89 tools", color: "text-cyan-400" },
              { label: "Psychometric Utility Theory", color: "text-amber-400" },
              { label: "soul-driven", color: "text-green-400" },
            ].map((tag) => (
              <span key={tag.label} className={`text-[9px] sm:text-[10px] font-medium ${tag.color}`}>
                {tag.label}
              </span>
            ))}
          </div>
          <a
            href="https://t.me/bluewave_wave_bot"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[9px] sm:text-[10px] text-white/30 hover:text-cyan-400 transition-colors shrink-0"
          >
            try on Telegram →
          </a>
        </div>
      </div>
    </motion.div>
  );
}

/* Floating particles for depth */
function Particles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 40 }).map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full bg-cyan-400/20"
          style={{
            width: `${Math.random() * 3 + 1}px`,
            height: `${Math.random() * 3 + 1}px`,
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            animation: `float${i % 3} ${12 + Math.random() * 20}s ease-in-out infinite`,
            animationDelay: `${Math.random() * 10}s`,
            opacity: Math.random() * 0.5 + 0.1,
          }}
        />
      ))}
    </div>
  );
}

interface HeroProps {
  isAuthenticated?: boolean;
}

export default function Hero({ isAuthenticated }: HeroProps) {
  const { t, geo } = useGeo();

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-b from-[#0a0a1a] to-[#111827]">
      {/* Animated ambient gradients */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute w-[900px] h-[900px] rounded-full blur-[200px] opacity-20"
          style={{
            background: "radial-gradient(circle, rgba(34,211,238,0.35) 0%, transparent 60%)",
            top: "5%", left: "20%",
            animation: "drift1 20s ease-in-out infinite",
          }} />
        <div className="absolute w-[700px] h-[700px] rounded-full blur-[180px] opacity-15"
          style={{
            background: "radial-gradient(circle, rgba(59,130,246,0.3) 0%, transparent 55%)",
            bottom: "5%", right: "15%",
            animation: "drift2 25s ease-in-out infinite",
          }} />
        <div className="absolute w-[500px] h-[500px] rounded-full blur-[160px] opacity-10"
          style={{
            background: "radial-gradient(circle, rgba(6,182,212,0.3) 0%, transparent 60%)",
            top: "40%", left: "50%",
            animation: "drift3 18s ease-in-out infinite",
          }} />
      </div>

      {/* Floating particles */}
      <Particles />

      <style>{`
        @keyframes drift1 { 0%, 100% { transform: translate(0, 0); } 33% { transform: translate(4%, -3%); } 66% { transform: translate(-3%, 4%); } }
        @keyframes drift2 { 0%, 100% { transform: translate(0, 0); } 33% { transform: translate(-5%, 2%); } 66% { transform: translate(3%, -4%); } }
        @keyframes drift3 { 0%, 100% { transform: translate(0, 0) scale(1); } 50% { transform: translate(-4%, 3%) scale(1.1); } }
        @keyframes float0 { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(-30px) translateX(10px); } }
        @keyframes float1 { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(20px) translateX(-15px); } }
        @keyframes float2 { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(-15px) translateX(-8px); } }
        @keyframes shimmer { 0% { background-position: 200% center; } 100% { background-position: -200% center; } }
        @keyframes glow-pulse { 0%, 100% { box-shadow: 0 0 20px rgba(59,130,246,0.3); } 50% { box-shadow: 0 0 40px rgba(59,130,246,0.6); } }
      `}</style>

      {/* Top nav bar */}
      <nav className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-4 sm:px-10 py-4 sm:py-5">
        <Link to="/" className="flex items-center gap-2">
          <Waves className="w-5 h-5 sm:w-6 sm:h-6 text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.6)]" />
          <span className="text-base sm:text-lg font-extrabold tracking-tight bg-gradient-to-r from-cyan-300 via-blue-400 to-cyan-300 bg-clip-text text-transparent drop-shadow-[0_0_12px_rgba(34,211,238,0.3)]" style={{backgroundSize: '200% auto', animation: 'shimmer 3s linear infinite'}}>Bluewave</span>
        </Link>
        <div className="flex items-center gap-2 sm:gap-3">
          {isAuthenticated ? (
            <Link
              to="/assets"
              className="inline-flex items-center gap-1.5 px-3 sm:px-5 py-2 rounded-lg bg-blue-600 text-white font-medium text-xs sm:text-sm hover:bg-blue-700 transition-all duration-150"
            >
              {t.ctaDashboard}
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="hidden sm:inline-flex px-3 py-2 text-xs sm:text-sm font-medium text-white/70 hover:text-white transition-colors"
              >
                {t.signIn}
              </Link>
              <Link
                to="/register"
                className="inline-flex items-center px-3 sm:px-5 py-2 rounded-lg bg-blue-600 text-white font-medium text-xs sm:text-sm hover:bg-blue-700 transition-all duration-150"
              >
                {t.cta}
              </Link>
            </>
          )}
        </div>
      </nav>

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center pt-20 sm:pt-0">
        {/* Headline — translated */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="text-3xl sm:text-5xl lg:text-[56px] font-bold text-[#F9FAFB] leading-tight tracking-tight"
        >
          {t.heroHeadline1}
          <br />
          <span className="bg-gradient-to-r from-cyan-300 via-blue-400 to-cyan-300 bg-clip-text text-transparent" style={{backgroundSize: '200% auto', animation: 'shimmer 4s linear infinite'}}>
            {t.heroHeadline2}
          </span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mt-4 sm:mt-6 text-base sm:text-xl text-[#9CA3AF] max-w-2xl mx-auto leading-relaxed px-2"
        >
          {t.heroSub}
        </motion.p>

        {/* Regional context banner */}
        {geo.regionalData && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20"
          >
            <span className="text-xs sm:text-sm text-amber-400">
              {geo.isLocal ? "📍" : "🇧🇷"} {geo.regionalData.stat}
            </span>
          </motion.div>
        )}

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 px-4"
        >
          {isAuthenticated ? (
            <Link
              to="/assets"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-lg bg-blue-600 text-white font-semibold text-lg hover:bg-blue-700 transition-all duration-150 hover:scale-[1.02]"
              style={{ animation: "glow-pulse 3s ease-in-out infinite" }}
            >
              {t.ctaDashboard}
              <ArrowRight className="w-5 h-5" />
            </Link>
          ) : (
            <>
              <Link
                to="/register"
                className="inline-flex items-center px-8 py-3.5 rounded-lg bg-blue-600 text-white font-semibold text-lg hover:bg-blue-700 transition-all duration-150 hover:scale-[1.02]"
                style={{ animation: "glow-pulse 3s ease-in-out infinite" }}
              >
                {t.cta}
              </Link>
              <a
                href="#features"
                className="inline-flex items-center px-8 py-3.5 rounded-lg border border-white/20 text-white font-semibold text-lg hover:bg-white/5 transition-all duration-150"
              >
                {t.ctaDemo}
              </a>
            </>
          )}
        </motion.div>

        {/* Real credentials strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="mt-16"
        >
          <div className="flex items-center justify-center gap-3 sm:gap-8 flex-wrap">
            {[
              { text: t.credentialTools, color: "text-cyan-400/70" },
              { text: t.credentialAgents, color: "text-blue-400/70" },
              { text: t.credentialBrand, color: "text-amber-400/70" },
              { text: t.credentialSoul, color: "text-green-400/70" },
            ].map((item) => (
              <span
                key={item.text}
                className={`text-[10px] sm:text-xs font-medium ${item.color} tracking-wide`}
              >
                {item.text}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Hero visual — Wave agent live terminal */}
        <HeroTerminal />
      </div>
    </section>
  );
}
