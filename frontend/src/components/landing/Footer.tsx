import { Waves } from "lucide-react";
import { useGeo } from "../../contexts/GeoContext";

export default function Footer() {
  const { t } = useGeo();

  const columns = [
    {
      title: t.footerProduct,
      links: [
        { label: t.footerFeatures, href: "#features" },
        { label: t.footerPricing, href: "#pricing" },
        { label: t.footerBrandGuardian, href: "/guardian" },
      ],
    },
    {
      title: t.footerConnect,
      links: [
        { label: "GitHub", href: "https://github.com/Galmanus/bluewave" },
        { label: "Moltbook", href: "https://www.moltbook.com/u/bluewaveprime" },
        { label: t.footerContact, href: "mailto:m.galmanus@gmail.com" },
      ],
    },
  ];

  return (
    <footer className="bg-[#0a0a1a] border-t border-white/5 py-16">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-10">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Waves className="w-6 h-6 text-blue-500" />
              <span className="text-lg font-bold text-white">Bluewave</span>
            </div>
            <p className="text-sm text-[#9CA3AF] leading-relaxed">
              AI creative operations agent
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-[#F9FAFB] mb-4">{col.title}</h4>
              <ul className="space-y-3">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <a href={link.href} className="text-sm text-[#9CA3AF] hover:text-white transition-colors">
                      {link.label}
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
