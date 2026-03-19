import { motion } from "framer-motion";
import { useState, useEffect, useRef } from "react";
import { Waves, ArrowRight, Bot, Search, Eye, Shield, BarChart3, Zap, Wallet } from "lucide-react";
import { Link } from "react-router-dom";
import { useWallet } from "../../hooks/useWallet";

function WaveCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let time = 0;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const drawWave = (
      yBase: number,
      amplitude: number,
      frequency: number,
      speed: number,
      color: string,
      lineWidth: number,
      phase: number
    ) => {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;

      for (let x = 0; x <= canvas.width; x += 2) {
        const y =
          yBase +
          Math.sin(x * frequency + time * speed + phase) * amplitude +
          Math.sin(x * frequency * 0.5 + time * speed * 0.7 + phase * 2) * amplitude * 0.5 +
          Math.sin(x * frequency * 2 + time * speed * 1.3) * amplitude * 0.2;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };

    const drawGlowWave = (
      yBase: number,
      amplitude: number,
      frequency: number,
      speed: number,
      r: number, g: number, b: number,
      phase: number
    ) => {
      // Glow layer (thick, transparent)
      drawWave(yBase, amplitude, frequency, speed, `rgba(${r},${g},${b},0.03)`, 40, phase);
      drawWave(yBase, amplitude, frequency, speed, `rgba(${r},${g},${b},0.06)`, 16, phase);
      drawWave(yBase, amplitude, frequency, speed, `rgba(${r},${g},${b},0.12)`, 6, phase);
      // Core line (thin, bright)
      drawWave(yBase, amplitude, frequency, speed, `rgba(${r},${g},${b},0.35)`, 2, phase);
      drawWave(yBase, amplitude, frequency, speed, `rgba(${r},${g},${b},0.6)`, 1, phase);
    };

    const animate = () => {
      time += 0.008;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const h = canvas.height;

      // Layer 1 — deep background wave (subtle)
      drawGlowWave(h * 0.3, 60, 0.003, 0.4, 59, 130, 246, 0);        // blue

      // Layer 2 — main wave (hero)
      drawGlowWave(h * 0.45, 80, 0.004, 0.6, 34, 211, 238, 1);       // cyan

      // Layer 3 — bright crest
      drawGlowWave(h * 0.55, 50, 0.005, 0.8, 34, 211, 238, 2.5);     // cyan bright

      // Layer 4 — secondary wave
      drawGlowWave(h * 0.65, 40, 0.006, 0.5, 6, 182, 212, 4);        // teal

      // Layer 5 — low accent
      drawGlowWave(h * 0.78, 30, 0.004, 0.3, 99, 102, 241, 3);       // indigo

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
      style={{ opacity: 0.7 }}
    />
  );
}

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
  { type: "divider", text: "" },
  { type: "input", text: "Hedera billing status?" },
  { type: "status", text: "Querying Mirror Node...", icon: "chain" },
  { type: "result", text: "1,247 actions — $62.35 revenue" },
  { type: "result", text: "Hedera: $0.12 vs Stripe: $18.14 (99.3% saved)" },
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
      className="mt-10 sm:mt-16 mx-auto max-w-3xl px-2 sm:px-0"
    >
      <div className="relative rounded-lg sm:rounded-xl border border-white/10 bg-[#0d1117] shadow-2xl shadow-blue-500/5 overflow-hidden">
        {/* Terminal chrome */}
        <div className="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 sm:py-3 bg-[#161b22] border-b border-white/5">
          <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-red-500/70" />
          <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-yellow-500/70" />
          <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-green-500/70" />
          <div className="ml-2 sm:ml-3 flex items-center gap-1.5 sm:gap-2 flex-1 min-w-0">
            <Bot className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-cyan-400 shrink-0" />
            <span className="text-[10px] sm:text-xs text-white/40 font-mono truncate">wave@bluewave</span>
            <span className="text-[9px] sm:text-[10px] text-green-400/60 ml-auto font-mono shrink-0 hidden sm:inline">58 tools active</span>
          </div>
        </div>

        {/* Terminal content */}
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

        {/* Bottom bar */}
        <div className="px-3 sm:px-4 py-2 bg-[#161b22] border-t border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2 sm:gap-4 flex-wrap">
            {[
              { label: "6 agents", color: "text-blue-400" },
              { label: "58 tools", color: "text-cyan-400" },
              { label: "Hedera", color: "text-purple-400" },
              { label: "self-evolving", color: "text-green-400" },
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

function LandingWalletButton() {
  const wallet = useWallet();

  if (!wallet.hasMetaMask) {
    return (
      <a
        href="https://metamask.io/download/"
        target="_blank"
        rel="noopener noreferrer"
        className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/10 text-xs font-medium text-white/50 hover:text-white hover:border-white/20 transition-all"
      >
        <Wallet className="h-3.5 w-3.5" />
        MetaMask
      </a>
    );
  }

  if (!wallet.address) {
    return (
      <button
        onClick={wallet.connect}
        disabled={wallet.isConnecting}
        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-purple-500/30 bg-purple-500/10 text-xs font-medium text-purple-300 hover:bg-purple-500/20 hover:border-purple-500/50 transition-all disabled:opacity-50"
      >
        <Wallet className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">{wallet.isConnecting ? "Connecting..." : "Connect Wallet"}</span>
        <span className="sm:hidden">{wallet.isConnecting ? "..." : "Wallet"}</span>
      </button>
    );
  }

  return (
    <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-green-500/20 bg-green-500/5">
      <div className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
      <span className="text-xs font-mono text-green-300">{wallet.shortAddress}</span>
      <span className="hidden sm:inline text-[10px] text-white/30">
        {wallet.balance ? `${parseFloat(wallet.balance).toFixed(1)} HBAR` : ""}
      </span>
    </div>
  );
}

interface HeroProps {
  isAuthenticated?: boolean;
}

export default function Hero({ isAuthenticated }: HeroProps) {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-b from-[#0a0a1a] to-[#111827]">
      {/* Ocean wave canvas */}
      <WaveCanvas />
      {/* Glow overlay for depth */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute w-[800px] h-[800px] rounded-full blur-[160px] opacity-30"
          style={{
            background: "radial-gradient(circle, rgba(34,211,238,0.4) 0%, transparent 60%)",
            top: "20%",
            left: "30%",
            animation: "glowDrift 10s ease-in-out infinite",
          }}
        />
      </div>
      <style>{`
        @keyframes glowDrift {
          0%, 100% { transform: translate(0, 0); opacity: 0.25; }
          50% { transform: translate(-5%, 3%); opacity: 0.4; }
        }
      `}</style>

      {/* Top nav bar */}
      <nav className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-4 sm:px-10 py-4 sm:py-5">
        <Link to="/" className="flex items-center gap-2">
          <Waves className="w-5 h-5 sm:w-6 sm:h-6 text-blue-500" />
          <span className="text-base sm:text-lg font-bold text-white tracking-tight">Bluewave</span>
        </Link>
        <div className="flex items-center gap-2 sm:gap-3">
          <LandingWalletButton />
          {isAuthenticated ? (
            <Link
              to="/assets"
              className="inline-flex items-center gap-1.5 px-3 sm:px-5 py-2 rounded-lg bg-blue-600 text-white font-medium text-xs sm:text-sm hover:bg-blue-700 transition-all duration-150"
            >
              Dashboard
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="hidden sm:inline-flex px-3 py-2 text-xs sm:text-sm font-medium text-white/70 hover:text-white transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="inline-flex items-center px-3 sm:px-5 py-2 rounded-lg bg-blue-600 text-white font-medium text-xs sm:text-sm hover:bg-blue-700 transition-all duration-150"
              >
                Start free
              </Link>
            </>
          )}
        </div>
      </nav>

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center pt-20 sm:pt-0">
        {/* Eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <span className="inline-flex items-center px-3 sm:px-4 py-1.5 rounded-full text-xs sm:text-sm font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
            Autonomous AI Agent &middot; 58 Tools &middot; Hedera
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-6 sm:mt-8 text-3xl sm:text-5xl lg:text-[56px] font-bold text-[#F9FAFB] leading-tight tracking-tight"
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
          className="mt-4 sm:mt-6 text-base sm:text-xl text-[#9CA3AF] max-w-2xl mx-auto leading-relaxed px-2"
        >
          An autonomous AI agent with 58 tools, 6 specialists, computer vision,
          sales prospecting, and self-evolving skills — billing on Hedera at 99.3% less cost.
        </motion.p>

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
          <p className="text-xs sm:text-sm text-[#9CA3AF] mb-4 sm:mb-6">
            Trusted by 500+ creative teams
          </p>
          <div className="flex items-center justify-center gap-4 sm:gap-12 opacity-40 flex-wrap">
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
