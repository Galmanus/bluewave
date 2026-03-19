import { motion } from "framer-motion";
import {
  LayoutGrid,
  Sparkles,
  CheckCircle2,
  Bot,
  Eye,
  Zap,
  Globe,
  Hexagon,
  BarChart3,
  Shield,
} from "lucide-react";

const ASSETS = [
  { img: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400&h=400&fit=crop", label: "Hero Banner", status: "Approved", color: "bg-emerald-500" },
  { img: "https://images.unsplash.com/photo-1634986666676-ec8fd927c23d?w=400&h=400&fit=crop", label: "Social Post", status: "Pending", color: "bg-amber-500" },
  { img: "https://images.unsplash.com/photo-1558591710-4b4a1ae0f04d?w=400&h=400&fit=crop", label: "Campaign", status: "Draft", color: "bg-zinc-500" },
  { img: "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=400&h=400&fit=crop", label: "Story Cover", status: "Approved", color: "bg-emerald-500" },
];

export default function Features() {
  return (
    <section id="features" className="py-20 sm:py-32 bg-[#0a0a1a]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-sm font-semibold text-blue-400 uppercase tracking-wider">
            What Wave can do
          </span>
          <h2 className="mt-3 text-3xl sm:text-4xl font-bold text-white leading-tight">
            One agent. Every creative operation.
          </h2>
          <p className="mt-4 text-base text-white/50 max-w-xl mx-auto">
            76 tools, 8 specialists, computer vision, behavioral intelligence, self-evolving skills — powered by Hedera and Psychometric Utility Theory.
          </p>
        </motion.div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

          {/* Card 1 — Asset Management (large) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="lg:col-span-2 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 relative overflow-hidden group hover:border-blue-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <LayoutGrid className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-semibold text-white">Asset Management</h3>
            </div>
            <p className="text-sm text-white/50 mb-5 max-w-md">
              Centralized library with AI-powered search, filtering, and instant status tracking. Every file organized, every version tracked.
            </p>
            <div className="grid grid-cols-4 gap-2">
              {ASSETS.map((a, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: i * 0.1 }}
                  className="aspect-square rounded-lg relative overflow-hidden"
                >
                  <img src={a.img} alt={a.label} className="w-full h-full object-cover" loading="lazy" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
                  <div className="absolute bottom-1.5 left-1.5 right-1.5 flex items-center justify-between">
                    <span className="text-[9px] text-white/80 font-medium truncate">{a.label}</span>
                    <div className={`w-1.5 h-1.5 rounded-full ${a.color} shrink-0`} />
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Card 2 — AI Vision */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 relative overflow-hidden group hover:border-purple-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <Eye className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-semibold text-white">Computer Vision</h3>
            </div>
            <p className="text-sm text-white/50 mb-5">
              Claude Vision analyzes every image — brand compliance scoring, OCR, A/B comparison.
            </p>
            <div className="rounded-lg relative overflow-hidden aspect-[4/3]">
              <img
                src="https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=500&h=375&fit=crop"
                alt="Workspace"
                className="w-full h-full object-cover"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent" />
              <div className="absolute bottom-3 left-3 right-3 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-white/70">Brand Compliance</span>
                  <span className="text-xs font-bold text-emerald-400">87/100</span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div className="h-full w-[87%] rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400" />
                </div>
                <div className="flex gap-1.5">
                  <span className="px-1.5 py-0.5 rounded text-[8px] bg-emerald-500/20 text-emerald-300">colors pass</span>
                  <span className="px-1.5 py-0.5 rounded text-[8px] bg-amber-500/20 text-amber-300">font mismatch</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Card 3 — AI Captions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 relative overflow-hidden group hover:border-cyan-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-semibold text-white">AI Captions</h3>
            </div>
            <p className="text-sm text-white/50 mb-5">
              Auto-generated captions, hashtags, and metadata in your brand voice.
            </p>
            <div className="space-y-3 rounded-lg bg-white/[0.03] border border-white/[0.06] p-4">
              <p className="text-xs text-white/70 italic leading-relaxed">
                "Modern workspace featuring collaborative team session focused on Q2 creative campaign development."
              </p>
              <div className="flex flex-wrap gap-1.5">
                {["#teamwork", "#creative", "#campaign", "#Q2", "#design"].map((tag) => (
                  <span key={tag} className="px-2 py-0.5 text-[10px] bg-cyan-500/10 text-cyan-300 rounded-full border border-cyan-500/20">
                    {tag}
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-1.5 pt-1">
                <Sparkles className="w-3 h-3 text-cyan-400" />
                <span className="text-[10px] text-cyan-400/70">Generated by Claude Vision</span>
              </div>
            </div>
          </motion.div>

          {/* Card 4 — Self-Evolving */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 relative overflow-hidden group hover:border-green-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <Zap className="w-5 h-5 text-green-400" />
              <h3 className="text-lg font-semibold text-white">Self-Evolving</h3>
            </div>
            <p className="text-sm text-white/50 mb-5">
              Wave creates new Python skills at runtime. Ask for a capability — he builds it.
            </p>
            <div className="font-mono text-[10px] leading-relaxed rounded-lg bg-[#0d1117] border border-white/[0.06] p-3 space-y-1">
              <div className="text-cyan-400">&gt; I need a Hacker News monitor</div>
              <div className="text-yellow-400/70">Creating skill: hacker_news_monitor.py</div>
              <div className="text-green-400/80">4 tools registered. 9KB. Live now.</div>
              <div className="text-white/30 mt-2">───────────────────</div>
              <div className="text-cyan-400">&gt; Monitor Product Hunt daily</div>
              <div className="text-yellow-400/70">Creating skill: producthunt_watcher.py</div>
              <div className="text-green-400/80">3 tools registered. Available.</div>
            </div>
          </motion.div>

          {/* Card 5 — Hedera (large) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.25 }}
            className="lg:col-span-2 rounded-2xl border border-white/[0.06] bg-gradient-to-br from-purple-500/[0.04] to-blue-500/[0.04] p-6 relative overflow-hidden group hover:border-purple-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <Hexagon className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-semibold text-white">Hedera-Powered Billing</h3>
              <span className="ml-auto px-2 py-0.5 text-[10px] font-bold bg-green-500/20 text-green-400 rounded-full">99.3% cheaper</span>
            </div>
            <p className="text-sm text-white/50 mb-5 max-w-lg">
              Every AI action settled as an HBAR micropayment. Every decision recorded on HCS. Users earn WAVE tokens.
            </p>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "HBAR Transfer", sublabel: "$0.0001 per tx", icon: "💸", color: "from-green-500/10 to-emerald-500/10 border-green-500/20" },
                { label: "HCS Audit Trail", sublabel: "Immutable log", icon: "🛡️", color: "from-blue-500/10 to-cyan-500/10 border-blue-500/20" },
                { label: "WAVE Token", sublabel: "Earn rewards", icon: "🪙", color: "from-purple-500/10 to-pink-500/10 border-purple-500/20" },
              ].map((item) => (
                <div
                  key={item.label}
                  className={`rounded-xl bg-gradient-to-br ${item.color} border p-4 text-center`}
                >
                  <span className="text-2xl">{item.icon}</span>
                  <p className="text-xs font-medium text-white mt-2">{item.label}</p>
                  <p className="text-[10px] text-white/40 mt-0.5">{item.sublabel}</p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Card 6 — Multi-Agent */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 relative overflow-hidden group hover:border-blue-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <Bot className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-semibold text-white">8 Specialists</h3>
            </div>
            <p className="text-sm text-white/50 mb-5">
              Wave delegates to domain experts. Each has tools, personality, and PUT framework.
            </p>
            <div className="space-y-2">
              {[
                { emoji: "🎨", name: "Curator", domain: "Asset management", tools: 10 },
                { emoji: "✅", name: "Director", domain: "Approval workflow", tools: 9 },
                { emoji: "🛡️", name: "Guardian", domain: "Brand compliance", tools: 6 },
                { emoji: "📊", name: "Strategist", domain: "Analytics + PUT", tools: 6 },
                { emoji: "✍️", name: "Creative", domain: "Content + Vectors", tools: 10 },
                { emoji: "⚙️", name: "Admin", domain: "Platform ops", tools: 10 },
                { emoji: "⚖️", name: "Legal", domain: "Compliance + IP", tools: 5 },
                { emoji: "🔒", name: "Security", domain: "OWASP + ATT&CK", tools: 5 },
              ].map((agent) => (
                <div key={agent.name} className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <span className="text-sm">{agent.emoji}</span>
                  <span className="text-xs font-medium text-white flex-1">{agent.name}</span>
                  <span className="text-[10px] text-white/30">{agent.tools} tools</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Card 7 — Prospecting */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.35 }}
            className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 relative overflow-hidden group hover:border-amber-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <Globe className="w-5 h-5 text-amber-400" />
              <h3 className="text-lg font-semibold text-white">Sales Prospecting</h3>
            </div>
            <p className="text-sm text-white/50 mb-5">
              Autonomous pipeline — find, research, qualify, and outreach. All from a chat message.
            </p>
            <div className="space-y-2 font-mono text-[10px]">
              <div className="flex items-center justify-between px-3 py-2 rounded bg-white/[0.03] border border-white/[0.06]">
                <span className="text-white/70">Yard NYC</span>
                <span className="text-emerald-400 font-bold">95/100</span>
              </div>
              <div className="flex items-center justify-between px-3 py-2 rounded bg-white/[0.03] border border-white/[0.06]">
                <span className="text-white/70">Anomaly</span>
                <span className="text-cyan-400 font-bold">82/100</span>
              </div>
              <div className="flex items-center justify-between px-3 py-2 rounded bg-white/[0.03] border border-white/[0.06]">
                <span className="text-white/70">R/GA</span>
                <span className="text-blue-400 font-bold">78/100</span>
              </div>
              <div className="text-center text-white/20 mt-1">BANT qualified + outreach ready</div>
            </div>
          </motion.div>

          {/* Card 8 — Behavioral Intelligence (PUT) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.42 }}
            className="lg:col-span-2 rounded-2xl border border-white/[0.06] bg-gradient-to-br from-amber-500/[0.03] to-orange-500/[0.03] p-6 relative overflow-hidden group hover:border-amber-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-5 h-5 text-amber-400" />
              <h3 className="text-lg font-semibold text-white">Psychometric Utility Theory</h3>
              <span className="ml-auto px-2 py-0.5 text-[10px] font-bold bg-amber-500/20 text-amber-400 rounded-full">Original Research</span>
            </div>
            <p className="text-sm text-white/50 mb-5 max-w-lg">
              Proprietary behavioral intelligence framework. Wave predicts purchase decisions using mathematical models derived from 3,000 years of strategic philosophy.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Utility Function", sublabel: "U = f(A,F,S,w,k)", desc: "Predicts decision state" },
                { label: "Shadow Coefficient", sublabel: "k (suppressed fear)", desc: "Hidden buying signals" },
                { label: "Desperation Factor", sublabel: "Omega sigmoid", desc: "Purchase timing" },
                { label: "7 Decision Vectors", sublabel: "Fear to Trust", desc: "Sales angle selection" },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-3"
                >
                  <p className="text-xs font-medium text-amber-300">{item.label}</p>
                  <p className="text-[10px] text-white/40 font-mono mt-1">{item.sublabel}</p>
                  <p className="text-[10px] text-white/25 mt-1">{item.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Card 9 — Security */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.45 }}
            className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 relative overflow-hidden group hover:border-red-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-red-400" />
              <h3 className="text-lg font-semibold text-white">Security Auditor</h3>
            </div>
            <p className="text-sm text-white/50 mb-5">
              MITRE ATT&CK + OWASP methodology. Thinks like an attacker, defends like an expert.
            </p>
            <div className="space-y-1.5 font-mono text-[10px]">
              {[
                { check: "OWASP Top 10", status: "90+ test cases" },
                { check: "MITRE ATT&CK", status: "Full TTP mapping" },
                { check: "Infrastructure", status: "Docker + DB + API" },
                { check: "Blockchain", status: "Wallet + tx security" },
              ].map((item) => (
                <div key={item.check} className="flex items-center justify-between px-3 py-1.5 rounded bg-white/[0.03] border border-white/[0.04]">
                  <span className="text-white/60">{item.check}</span>
                  <span className="text-red-400">{item.status}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Card 10 — Approval Workflow */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 relative overflow-hidden group hover:border-emerald-500/20 transition-colors"
          >
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <h3 className="text-lg font-semibold text-white">Approval Workflows</h3>
            </div>
            <p className="text-sm text-white/50 mb-5">
              Draft → Pending → Approved. No more email chains. No more "which version?"
            </p>
            <div className="flex items-center justify-center gap-2 py-4">
              {[
                { label: "Draft", color: "bg-zinc-500", ring: "ring-zinc-500/30" },
                { label: "Pending", color: "bg-amber-500", ring: "ring-amber-500/30" },
                { label: "Approved", color: "bg-emerald-500", ring: "ring-emerald-500/30" },
              ].map((step, i) => (
                <div key={step.label} className="flex items-center gap-2">
                  <div className="flex flex-col items-center gap-1.5">
                    <div className={`w-8 h-8 rounded-full ${step.color} ring-4 ${step.ring} flex items-center justify-center`}>
                      {i === 2 && <CheckCircle2 className="w-4 h-4 text-white" />}
                    </div>
                    <span className="text-[10px] text-white/50">{step.label}</span>
                  </div>
                  {i < 2 && <div className="w-8 h-px bg-white/10 mb-5" />}
                </div>
              ))}
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
}
