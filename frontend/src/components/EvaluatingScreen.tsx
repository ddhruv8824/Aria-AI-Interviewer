"use client";

import { Loader2 } from "lucide-react";
import { motion } from "motion/react";

export function EvaluatingScreen() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="flex flex-col items-center rounded-3xl border border-auralis bg-card-auralis px-8 py-20 text-center"
    >
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-auralis bg-surface shadow-lg">
        <Loader2 className="h-8 w-8 animate-spin text-primary" strokeWidth={1.75} />
      </div>
      <h2 className="mb-3 text-3xl font-semibold tracking-tighter text-primary md:text-4xl">
        Evaluating your interview
      </h2>
      <p className="max-w-md text-lg leading-relaxed text-secondary-auralis">
        Our AI judge is reviewing your responses and building your scorecard…
      </p>
    </motion.section>
  );
}
