"use client";

import { ArrowRight, Building2 } from "lucide-react";
import { motion } from "motion/react";
import { getHomeUrl } from "@/lib/api";

export function PracticeGateScreen() {
  const homeUrl = getHomeUrl();

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="mx-auto max-w-xl rounded-3xl border border-auralis bg-card-auralis p-10 text-center"
    >
      <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-full border border-auralis bg-panel-auralis">
        <Building2 className="h-6 w-6 text-primary" strokeWidth={1.75} />
      </div>
      <h1 className="text-3xl font-semibold tracking-tight text-primary">
        Choose a company to practise
      </h1>
      <p className="mt-4 text-base leading-relaxed text-secondary-auralis">
        The interview app opens after you pick a company track and enter your email on the
        Auralis homepage.
      </p>
      <a
        href={homeUrl}
        className="mt-8 inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-medium text-on-primary transition-all hover:bg-black/80"
      >
        Go to homepage
        <ArrowRight className="h-4 w-4" />
      </a>
    </motion.section>
  );
}
