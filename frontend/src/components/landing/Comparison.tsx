import { motion } from "framer-motion";
import { Check, X } from "lucide-react";
import { useGeo } from "../../contexts/GeoContext";

interface CellValue {
  type: "check" | "x" | "partial" | "text";
  label?: string;
}

const features: { name: string; values: CellValue[] }[] = [
  {
    name: "AI-powered captions",
    values: [
      { type: "check" },
      { type: "check" },
      { type: "x" },
      { type: "x" },
      { type: "x" },
    ],
  },
  {
    name: "Approval workflows",
    values: [
      { type: "check" },
      { type: "check" },
      { type: "partial", label: "Partial" },
      { type: "x" },
      { type: "x" },
    ],
  },
  {
    name: "Transparent pricing",
    values: [
      { type: "check" },
      { type: "x" },
      { type: "check" },
      { type: "check" },
      { type: "check" },
    ],
  },
  {
    name: "Brand compliance scoring (0-100)",
    values: [
      { type: "check" },
      { type: "x" },
      { type: "x" },
      { type: "x" },
      { type: "x" },
    ],
  },
  {
    name: "Self-serve onboarding",
    values: [
      { type: "text", label: "< 5 min" },
      { type: "text", label: "Weeks" },
      { type: "check" },
      { type: "check" },
      { type: "check" },
    ],
  },
  {
    name: "Multi-tenant isolation",
    values: [
      { type: "check" },
      { type: "check" },
      { type: "check" },
      { type: "check" },
      { type: "x" },
    ],
  },
  {
    name: "Free tier",
    values: [
      { type: "check" },
      { type: "x" },
      { type: "text", label: "5 GB" },
      { type: "text", label: "2 GB" },
      { type: "text", label: "15 GB" },
    ],
  },
  {
    name: "Role-based access",
    values: [
      { type: "check" },
      { type: "check" },
      { type: "check" },
      { type: "check" },
      { type: "partial", label: "Partial" },
    ],
  },
  {
    name: "Starting price",
    values: [
      { type: "text", label: "$12/user" },
      { type: "text", label: "~$450/mo" },
      { type: "text", label: "$10/user" },
      { type: "text", label: "$15/user" },
      { type: "text", label: "$6/user" },
    ],
  },
];

const competitors = ["Bluewave", "Bynder", "Air.inc", "Frame.io", "Google Drive"];

function CellContent({ cell }: { cell: CellValue }) {
  switch (cell.type) {
    case "check":
      return <Check className="w-5 h-5 text-emerald-500 mx-auto" />;
    case "x":
      return <X className="w-5 h-5 text-white/20 mx-auto" />;
    case "partial":
      return (
        <span className="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
          {cell.label}
        </span>
      );
    case "text":
      return (
        <span className="text-sm font-medium text-[#374151]">{cell.label}</span>
      );
  }
}

export default function Comparison() {
  const { t } = useGeo();
  return (
    <section className="py-24 sm:py-32 bg-[#0a0a1a]">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-white leading-tight">
            {t.compTitle}
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="overflow-x-auto"
        >
          <table className="w-full min-w-[640px]">
            <thead>
              <tr>
                <th className="text-left py-4 px-4 text-sm font-medium text-[#9CA3AF]">
                  Feature
                </th>
                {competitors.map((c, i) => (
                  <th
                    key={c}
                    className={`py-4 px-4 text-center text-sm font-semibold ${
                      i === 0
                        ? "text-blue-600 bg-blue-50/50 rounded-t-lg"
                        : "text-[#374151]"
                    }`}
                  >
                    {c}
                    {i === 0 && (
                      <span className="block text-[10px] font-medium text-blue-500 mt-0.5">
                        Recommended
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {features.map((row, ri) => (
                <motion.tr
                  key={row.name}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: 0.3 + ri * 0.05 }}
                  className="border-t border-white/[0.06]"
                >
                  <td className="py-4 px-4 text-sm font-medium text-[#374151]">
                    {row.name}
                  </td>
                  {row.values.map((cell, ci) => (
                    <td
                      key={ci}
                      className={`py-4 px-4 text-center ${
                        ci === 0 ? "bg-blue-50/50" : ""
                      }${
                        ri === features.length - 1 && ci === 0
                          ? " rounded-b-lg"
                          : ""
                      }`}
                    >
                      <CellContent cell={cell} />
                    </td>
                  ))}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      </div>
    </section>
  );
}
