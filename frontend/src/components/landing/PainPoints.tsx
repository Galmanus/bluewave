import { motion } from "framer-motion";
import { FolderSearch, MessageSquareWarning, RotateCcw } from "lucide-react";

const cards = [
  {
    icon: FolderSearch,
    title: "Scattered everywhere",
    description:
      "Your assets live across 5+ tools — Drive, Dropbox, email, Slack, someone's desktop. Nobody can find anything.",
    stat: "51% of workers spend 2+ hours/day searching for files",
  },
  {
    icon: MessageSquareWarning,
    title: "Approval chaos",
    description:
      "Feedback comes via email, Slack, marked-up PDFs, and phone calls. Versions multiply. Deadlines slip.",
    stat: "52% of companies miss deadlines due to approval delays",
  },
  {
    icon: RotateCcw,
    title: "Wasted money",
    description:
      "You're paying designers to recreate assets that already exist somewhere — you just can't find them.",
    stat: "51% of marketers recreate assets because originals are lost",
  },
];

export default function PainPoints() {
  return (
    <section className="py-24 sm:py-32 bg-[#FAFAFA]">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-sm font-semibold text-red-500/80 uppercase tracking-wider">
            The problem
          </span>
          <h2 className="mt-3 text-3xl sm:text-4xl font-bold text-[#111827] leading-tight">
            Your creative workflow is broken
          </h2>
          <p className="mt-4 text-lg text-[#6b7280]">Sound familiar?</p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {cards.map((card, i) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.15 }}
              className="bg-white rounded-xl p-8 border border-gray-100 shadow-sm hover:-translate-y-1 hover:shadow-md transition-all duration-200"
            >
              <div className="w-12 h-12 rounded-lg bg-red-50 flex items-center justify-center mb-6">
                <card.icon className="w-6 h-6 text-red-500/80" />
              </div>
              <h3 className="text-xl font-semibold text-[#111827] mb-3">
                {card.title}
              </h3>
              <p className="text-[#6b7280] leading-relaxed mb-6">
                {card.description}
              </p>
              <p className="text-sm font-semibold text-red-600/80 bg-red-50 px-4 py-2 rounded-lg">
                {card.stat}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
