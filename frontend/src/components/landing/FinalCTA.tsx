import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

interface FinalCTAProps {
  isAuthenticated?: boolean;
}

export default function FinalCTA({ isAuthenticated }: FinalCTAProps) {
  return (
    <section className="relative py-24 sm:py-32 bg-gradient-to-b from-[#111827] to-[#0a0a1a] overflow-hidden">
      {/* Aurora effect */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-blue-500/8 blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 rounded-full bg-indigo-500/5 blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-3xl mx-auto px-6 text-center">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-3xl sm:text-4xl lg:text-5xl font-bold text-[#F9FAFB] leading-tight"
        >
          Stop doing what an AI agent should do for you.
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mt-6 text-lg text-[#9CA3AF]"
        >
          Upload an image. Get an 8-dimension compliance report in seconds. Free.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          {isAuthenticated ? (
            <Link
              to="/assets"
              className="inline-flex items-center gap-2 px-10 py-4 rounded-lg bg-blue-600 text-white font-semibold text-lg hover:bg-blue-700 transition-all duration-150 hover:scale-[1.02] hover:shadow-[0_0_32px_rgba(37,99,235,0.5)]"
            >
              Open Dashboard
              <ArrowRight className="w-5 h-5" />
            </Link>
          ) : (
            <>
              <Link
                to="/register"
                className="inline-flex items-center px-10 py-4 rounded-lg bg-blue-600 text-white font-semibold text-lg hover:bg-blue-700 transition-all duration-150 hover:scale-[1.02] hover:shadow-[0_0_32px_rgba(37,99,235,0.5)]"
              >
                Deploy your AI agent — free
              </Link>
              <a
                href="mailto:sales@bluewave.app"
                className="inline-flex items-center px-8 py-4 rounded-lg border border-white/20 text-white font-semibold hover:bg-white/5 transition-all duration-150"
              >
                Book a demo
              </a>
            </>
          )}
        </motion.div>
      </div>
    </section>
  );
}
