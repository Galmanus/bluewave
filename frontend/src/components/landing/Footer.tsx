import { Waves } from "lucide-react";

const columns = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "#features" },
      { label: "Pricing", href: "#pricing" },
      { label: "Brand Guardian", href: "/guardian" },
    ],
  },
  {
    title: "Connect",
    links: [
      { label: "GitHub", href: "https://github.com/Galmanus/bluewave" },
      { label: "Moltbook", href: "https://www.moltbook.com/u/bluewaveprime" },
      { label: "Contact", href: "mailto:m.galmanus@gmail.com" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="bg-[#0a0a1a] border-t border-white/5 py-16">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
          {/* Brand column */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <Waves className="w-6 h-6 text-blue-500" />
              <span className="text-lg font-bold text-white">Bluewave</span>
            </div>
            <p className="text-sm text-[#9CA3AF] leading-relaxed">
              AI creative operations agent
            </p>
          </div>

          {/* Link columns */}
          {columns.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-[#F9FAFB] mb-4">
                {col.title}
              </h4>
              <ul className="space-y-3">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-[#9CA3AF] hover:text-white transition-colors"
                    >
                      {link.label}
                      {"badge" in link && link.badge && (
                        <span className="ml-2 text-[10px] text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                          {link.badge}
                        </span>
                      )}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-8 border-t border-white/5">
          <p className="text-xs text-[#9CA3AF] text-center">
            &copy; {new Date().getFullYear()} Bluewave. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
