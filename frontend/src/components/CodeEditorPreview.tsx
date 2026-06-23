"use client";

import { motion } from "motion/react";
import CodingQuestion, { numberClassifierProblem } from "@/components/CodingQuestion";

export function CodeEditorPreview() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="rounded-3xl border border-auralis bg-panel-auralis p-8"
    >
      <div className="mb-8 flex items-center gap-4">
        <span className="rounded-full bg-surface-variant px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-primary">
          Preview · Coding challenge
        </span>
        <div className="h-px flex-1 bg-auralis" />
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
        <div className="lg:col-span-7">
          <h2 className="text-3xl font-semibold tracking-tighter text-primary md:text-[40px]">
            Try the code editor
          </h2>
        </div>
        <div className="lg:col-span-5">
          <p className="text-base leading-relaxed text-secondary-auralis">
            LeetCode-style editor with run &amp; test (Python or JavaScript, runs locally). During the
            live interview, {` `}
            you&apos;ll get a timed coding round after the verbal section.
          </p>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-auralis bg-card-auralis">
        <CodingQuestion problem={numberClassifierProblem} />
      </div>
    </motion.section>
  );
}
