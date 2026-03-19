import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { Waves, ArrowRight, Bot, Search, Eye, Shield, BarChart3, Zap } from "lucide-react";
import { Link } from "react-router-dom";

const TERMINAL_LINES = [
  { type: "input", text: "wave, find me creative agencies struggling with content ops" },
  { type: "status", text: "Searching web + LinkedIn + X/Twitter...", icon: "search" },
  { type: "status", text: "Delegating to Strategist for market analysis...", icon: "agent" },
  { type: "output", text: "Found 5 prospects. Top match:" },
  { type: "result", text: "Yard NYC — Score: 95/100 (AdAge Small Agency of the Year)" },
  { type: "result", text: "CEO: Ruth Bernstein | 96 employees | Clients: Tanqueray, Walmart" },
  { type: "result", text: "Pain signal: content ops bottleneck with tier-1 clients" },
  { type: "status", text: "Generating 4-touch outreach sequence...", icon: "zap" },
  { type: "output", text: "Outreach ready. Day 1: Email, Day 2: LinkedIn, Day 5: Follow-up, Day 10: Close" },
  { type: "divider", text: "" },
  { type: "input", text: "analyze this image for brand compliance" },
  { type: "status", text: "Claude Vision analyzing image...", icon: "eye" },
  { type: "result", text: "Compliance: 87/100 — Colors match, typography off-brand" },
  { type: "result", text: "Issue: Using Helvetica instead of Inter (x-height differs 7%)" },
  { type: "result", text: "Suggestion: Switch to Inter with fallback system-ui" },
  { type: "divider", text: "" },
  { type: "input", text: "I need a Hacker News monitor" },
  { type: "status", text: "Creating skill: hacker_news_monitor.py...", icon: "zap" },
  { type: "output", text: "Skill created! 4 new tools: hn_top, hn_search, hn_comments, hn_monitor" },
  { type: "result", text: "9KB of Python generated, validated, registered. Available now." },
  { type: "divider", text: "" },
  { type: "input", text: "what's our Hedera billing status?" },
  { type: "status", text: "Querying Hedera Mirror Node...", icon: "chain" },
  { type: "result", text: "1,247 AI actions this month — $62.35 revenue" },
  { type: "result", text: "Hedera tx fees: $0.12 total (vs $18.14 on Stripe)" },
  { type: "result", text: "Savings: $18.02 (99.3% cheaper)" },
];

function HeroTerminal() {
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setVisibleLines((prev) => {
        if (prev >= TERMINAL_LINES.length) {
          // Reset after showing all
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
      className="mt-16 mx-auto max-w-3xl"
    >
      <div className="relative rounded-xl border border-white/10 bg-[#0d1117] shadow-2xl shadow-blue-500/5 overflow-hidden">
        {/* Terminal chrome */}
        <div className="flex items-center gap-2 px-4 py-3 bg-[#161b22] border-b border-white/5">
          <div className="w-3 h-3 rounded-full bg-red-500/70" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
          <div className="w-3 h-3 rounded-full bg-green-500/70" />
          <div className="ml-3 flex items-center gap-2 flex-1">
            <Bot className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs text-white/40 font-mono">wave@bluewave</span>
            <span className="text-[10px] text-green-400/60 ml-auto font-mono">58 tools active</span>
          </div>
        </div>

        {/* Terminal content */}
        <div className="p-4 sm:p-5 font-mono text-[12px] sm:text-[13px] leading-relaxed h-[340px] overflow-hidden">
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

        {/* Bottom bar */}
        <div className="px-4 py-2 bg-[#161b22] border-t border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {[
              { label: "6 agents", color: "text-blue-400" },
              { label: "58 tools", color: "text-cyan-400" },
              { label: "Hedera", color: "text-purple-400" },
              { label: "self-evolving", color: "text-green-400" },
            ].map((tag) => (
              <span key={tag.label} className={`text-[10px] font-medium ${tag.color}`}>
                {tag.label}
              </span>
            ))}
          </div>
          <a
            href="https://t.me/bluewave_wave_bot"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-white/30 hover:text-cyan-400 transition-colors"
          >
            try live on Telegram →
          </a>
        </div>
      </div>
    </motion.div>
  );
}

interface HeroProps {
  isAuthenticated?: boolean;
}

export default function Hero({ isAuthenticated }: HeroProps) {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-b from-[#0a0a1a] to-[#111827]">
      {/* Animated gradient mesh */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full rounded-full bg-blue-500/10 blur-[120px] animate-pulse" />
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full rounded-full bg-indigo-500/8 blur-[120px] animate-pulse [animation-delay:2s]" />
        <div className="absolute top-1/4 right-1/4 w-96 h-96 rounded-full bg-cyan-500/5 blur-[100px] animate-pulse [animation-delay:4s]" />
      </div>

      {/* Top nav bar */}
      <nav className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-6 sm:px-10 py-5">
        <Link to="/" className="flex items-center gap-2">
          <Waves className="w-6 h-6 text-blue-500" />
          <span className="text-lg font-bold text-white tracking-tight">Bluewave</span>
        </Link>
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <Link
              to="/assets"
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-blue-600 text-white font-medium text-sm hover:bg-blue-700 transition-all duration-150"
            >
              Go to Dashboard
              <ArrowRight className="w-4 h-4" />
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="px-4 py-2 text-sm font-medium text-white/70 hover:text-white transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="inline-flex items-center px-5 py-2 rounded-lg bg-blue-600 text-white font-medium text-sm hover:bg-blue-700 transition-all duration-150"
              >
                Start free
              </Link>
            </>
          )}
        </div>
      </nav>

      <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
        {/* Eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <span className="inline-flex items-center px-4 py-1.5 rounded-full text-sm font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
            Autonomous AI Agent &middot; 58 Tools &middot; Hedera-Powered
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-8 text-4xl sm:text-5xl lg:text-[56px] font-bold text-[#F9FAFB] leading-tight tracking-tight"
        >
          You upload.
          <br />
          The agent does the rest.
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-6 text-lg sm:text-xl text-[#9CA3AF] max-w-2xl mx-auto leading-relaxed"
        >
          An autonomous AI agent with 58 tools, 6 specialists, computer vision,
          sales prospecting, and self-evolving skills — billing on Hedera at 99.3% less cost.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          {isAuthenticated ? (
            <Link
              to="/assets"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-lg bg-blue-600 text-white font-semibold text-lg hover:bg-blue-700 transition-all duration-150 hover:scale-[1.02] hover:shadow-[0_0_24px_rgba(37,99,235,0.4)]"
            >
              Open Dashboard
              <ArrowRight className="w-5 h-5" />
            </Link>
          ) : (
            <>
              <Link
                to="/register"
                className="inline-flex items-center px-8 py-3.5 rounded-lg bg-blue-600 text-white font-semibold text-lg hover:bg-blue-700 transition-all duration-150 hover:scale-[1.02] hover:shadow-[0_0_24px_rgba(37,99,235,0.4)]"
              >
                Start free
              </Link>
              <a
                href="#features"
                className="inline-flex items-center px-8 py-3.5 rounded-lg border border-white/20 text-white font-semibold text-lg hover:bg-white/5 transition-all duration-150"
              >
                Watch demo
              </a>
            </>
          )}
        </motion.div>

        {/* Social proof strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="mt-16"
        >
          <p className="text-sm text-[#9CA3AF] mb-6">
            Trusted by 500+ creative teams
          </p>
          <div className="flex items-center justify-center gap-8 sm:gap-12 opacity-40">
            {["Acme Studio", "PixelCo", "MediaFlow", "CreativeHub", "BrandLab"].map(
              (name) => (
                <span
                  key={name}
                  className="text-sm font-semibold text-white/60 tracking-wide uppercase"
                >
                  {name}
                </span>
              )
            )}
          </div>
        </motion.div>

        {/* Hero visual — Wave agent live terminal */}
        <HeroTerminal />
      </div>
    </section>
  );
}
