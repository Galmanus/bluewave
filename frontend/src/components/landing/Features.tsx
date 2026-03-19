import { motion } from "framer-motion";
import {
  LayoutGrid,
  Sparkles,
  CheckCircle2,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface Feature {
  icon: LucideIcon;
  headline: string;
  body: string;
  badge: string;
  mockup: React.ReactNode;
}

function AssetGridMockup() {
  const tabs = ["All", "Draft", "Pending", "Approved"];
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-lg overflow-hidden">
      <div className="flex gap-1 px-4 pt-4 border-b border-gray-100 pb-3">
        {tabs.map((t, i) => (
          <span
            key={t}
            className={`px-3 py-1 text-xs font-medium rounded-md ${
              i === 0
                ? "bg-blue-600 text-white"
                : "text-gray-500 hover:bg-gray-50"
            }`}
          >
            {t}
          </span>
        ))}
      </div>
      <div className="p-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { img: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400&h=400&fit=crop", label: "Hero Banner", status: "Approved", statusColor: "bg-emerald-100 text-emerald-700" },
          { img: "https://images.unsplash.com/photo-1634986666676-ec8fd927c23d?w=400&h=400&fit=crop", label: "Social Post", status: "Pending", statusColor: "bg-amber-100 text-amber-700" },
          { img: "https://images.unsplash.com/photo-1558591710-4b4a1ae0f04d?w=400&h=400&fit=crop", label: "Campaign", status: "Draft", statusColor: "bg-gray-100 text-gray-500" },
          { img: "https://images.unsplash.com/photo-1614850715649-1d0106568571?w=400&h=400&fit=crop", label: "Product Shot", status: "Approved", statusColor: "bg-emerald-100 text-emerald-700" },
          { img: "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=400&h=400&fit=crop", label: "Story Cover", status: "Pending", statusColor: "bg-amber-100 text-amber-700" },
          { img: "https://images.unsplash.com/photo-1557672172-298e090bd0f1?w=400&h=400&fit=crop", label: "Brand Kit", status: "Approved", statusColor: "bg-emerald-100 text-emerald-700" },
        ].map((item, i) => (
          <div
            key={i}
            className="aspect-square rounded-lg relative overflow-hidden group"
          >
            <img src={item.img} alt={item.label} className="absolute inset-0 w-full h-full object-cover" loading="lazy" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
            <div className="absolute inset-0 flex flex-col items-start justify-end p-2.5">
              <span className="text-[10px] font-medium text-white drop-shadow-sm">{item.label}</span>
              <span className={`mt-1 text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${item.statusColor}`}>
                {item.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AICaptionMockup() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-lg overflow-hidden p-5">
      <div className="aspect-video rounded-lg relative overflow-hidden mb-4">
        <img
          src="https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=600&h=340&fit=crop"
          alt="Team workspace"
          className="w-full h-full object-cover"
          loading="lazy"
        />
        <div className="absolute top-2 right-2 flex items-center gap-1 bg-blue-600/90 backdrop-blur-sm px-2 py-1 rounded-md">
          <Sparkles className="w-3 h-3 text-white" />
          <span className="text-[10px] font-semibold text-white">AI Generated</span>
        </div>
      </div>
      <div className="space-y-3">
        <div>
          <span className="text-xs font-semibold text-gray-400 uppercase">
            AI Caption
          </span>
          <p className="mt-1 text-sm text-gray-700">
            Modern office workspace with team collaboration on creative
            campaign assets for Q2 product launch.
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {["#teamwork", "#creative", "#campaign", "#Q2launch", "#design"].map(
            (tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 text-xs bg-blue-50 text-blue-600 rounded-full"
              >
                {tag}
              </span>
            )
          )}
        </div>
      </div>
    </div>
  );
}

function ApprovalMockup() {
  const steps = [
    { label: "Draft", color: "bg-gray-400" },
    { label: "Pending", color: "bg-amber-400" },
    { label: "Approved", color: "bg-emerald-500" },
  ];
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-lg overflow-hidden p-5">
      <div className="flex items-center gap-3 mb-6">
        {steps.map((s, i) => (
          <div key={s.label} className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${s.color}`} />
              <span className="text-sm font-medium text-gray-700">
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className="w-8 h-px bg-gray-200" />
            )}
          </div>
        ))}
      </div>
      <div className="space-y-3">
        {[
          { file: "brand-guidelines-v3.pdf", thumb: "https://images.unsplash.com/photo-1626785774573-4b799315345d?w=80&h=80&fit=crop", step: 2 },
          { file: "hero-banner-final.png", thumb: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=80&h=80&fit=crop", step: 1 },
          { file: "social-pack.zip", thumb: "https://images.unsplash.com/photo-1557672172-298e090bd0f1?w=80&h=80&fit=crop", step: 0 },
        ].map(
          (item, i) => (
            <div
              key={item.file}
              className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50"
            >
              <div className="flex items-center gap-3">
                <img src={item.thumb} alt="" className="w-8 h-8 rounded object-cover" loading="lazy" />
                <span className="text-sm text-gray-600">{item.file}</span>
              </div>
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  item.step === 2
                    ? "bg-emerald-100 text-emerald-700"
                    : item.step === 1
                    ? "bg-amber-100 text-amber-700"
                    : "bg-gray-100 text-gray-500"
                }`}
              >
                {steps[item.step].label}
              </span>
            </div>
          )
        )}
      </div>
    </div>
  );
}

function TeamMockup() {
  const members = [
    { name: "Sarah K.", role: "Admin", color: "bg-blue-100 text-blue-700", avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&h=80&fit=crop&crop=face" },
    { name: "James L.", role: "Editor", color: "bg-emerald-100 text-emerald-700", avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&h=80&fit=crop&crop=face" },
    { name: "Maria R.", role: "Viewer", color: "bg-gray-100 text-gray-600", avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=80&h=80&fit=crop&crop=face" },
  ];
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-lg overflow-hidden p-5">
      <div className="space-y-3">
        {members.map((m) => (
          <div
            key={m.name}
            className="flex items-center justify-between px-3 py-3 rounded-lg bg-gray-50"
          >
            <div className="flex items-center gap-3">
              <img src={m.avatar} alt={m.name} className="w-8 h-8 rounded-full object-cover" loading="lazy" />
              <span className="text-sm font-medium text-gray-700">
                {m.name}
              </span>
            </div>
            <span
              className={`text-xs font-medium px-2.5 py-1 rounded-full ${m.color}`}
            >
              {m.role}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const features: Feature[] = [
  {
    icon: LayoutGrid,
    headline: "Every asset. One workspace.",
    body: "Upload images and videos to a centralized, searchable library. Filter by status, type, or campaign. No more digging through folders.",
    badge: "Replaces Google Drive + Dropbox + email",
    mockup: <AssetGridMockup />,
  },
  {
    icon: Sparkles,
    headline: "AI captions and hashtags — automatically",
    body: "Upload a file and Bluewave's AI generates captions, hashtags, and metadata instantly. Edit or regenerate with one click. Spend time on creative, not data entry.",
    badge: "Saves 3+ hours/week per team member",
    mockup: <AICaptionMockup />,
  },
  {
    icon: CheckCircle2,
    headline: "Submit. Review. Approve. Done.",
    body: "Built-in approval workflows replace email chains. Editors submit, admins approve or reject with comments. Everyone sees the same status. No more 'which version is final?'",
    badge: "Cuts approval cycle time by 40%",
    mockup: <ApprovalMockup />,
  },
  {
    icon: Users,
    headline: "Roles that make sense",
    body: "Admins, editors, and viewers — each sees exactly what they need. Invite your team in seconds. Multi-tenant architecture means your data is yours alone.",
    badge: "Admin \u2022 Editor \u2022 Viewer roles",
    mockup: <TeamMockup />,
  },
];

export default function Features() {
  return (
    <section id="features" className="py-24 sm:py-32">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="text-sm font-semibold text-blue-600 uppercase tracking-wider">
            The solution
          </span>
          <h2 className="mt-3 text-3xl sm:text-4xl font-bold text-[#111827] leading-tight">
            Everything your team needs, nothing it doesn't
          </h2>
        </motion.div>

        <div className="space-y-24 sm:space-y-32">
          {features.map((feature, i) => {
            const isReversed = i % 2 === 1;
            return (
              <div
                key={feature.headline}
                className={`flex flex-col ${
                  isReversed ? "lg:flex-row-reverse" : "lg:flex-row"
                } items-center gap-12 lg:gap-16`}
              >
                <motion.div
                  initial={{ opacity: 0, x: isReversed ? 30 : -30 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6 }}
                  className="flex-1"
                >
                  <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center mb-6">
                    <feature.icon className="w-6 h-6 text-blue-600" />
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#111827] mb-4">
                    {feature.headline}
                  </h3>
                  <p className="text-lg text-[#6b7280] leading-relaxed mb-6">
                    {feature.body}
                  </p>
                  <span className="inline-flex items-center px-4 py-1.5 rounded-full text-sm font-medium bg-blue-50 text-blue-600">
                    {feature.badge}
                  </span>
                </motion.div>
                <motion.div
                  initial={{ opacity: 0, x: isReversed ? -30 : 30 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.2 }}
                  className="flex-1 w-full max-w-lg"
                >
                  {feature.mockup}
                </motion.div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
