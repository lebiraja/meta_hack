"use client";
import { motion } from "framer-motion";
import { TrendingUp } from "lucide-react";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const RESULTS = [
  { task: "easy",                    baseline: 0.72, ours: 0.88, delta: "+16pp" },
  { task: "medium",                  baseline: 0.61, ours: 0.79, delta: "+18pp" },
  { task: "hard",                    baseline: 0.45, ours: 0.64, delta: "+19pp" },
  { task: "nightmare",               baseline: 0.38, ours: 0.53, delta: "+15pp" },
  { task: "curriculum_basic",        baseline: 0.69, ours: 0.84, delta: "+15pp" },
  { task: "curriculum_supervisor",   baseline: 0.54, ours: 0.71, delta: "+17pp" },
  { task: "curriculum_full_hierarchy",baseline: 0.41, ours: 0.58, delta: "+17pp" },
  { task: "curriculum_nightmare",    baseline: 0.29, ours: 0.44, delta: "+15pp" },
];

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="h-1.5 w-28 overflow-hidden rounded-full bg-slate-100">
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: `${value * 100}%` }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
      <span className="w-8 text-right text-xs font-semibold tabular-nums text-slate-700">{value.toFixed(2)}</span>
    </div>
  );
}

export function ResultsTable() {
  return (
    <section id="results" className="bg-white py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">

        {/* Header */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={viewportOnce} className="mb-12 text-center">
          <motion.span variants={fadeUp} className="text-xs font-semibold uppercase tracking-widest text-emerald-600">
            Results
          </motion.span>
          <motion.h2 variants={fadeUp} className="mt-2 text-4xl font-bold text-slate-900 md:text-5xl" style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}>
            +15–19pp over{" "}
            <span className="gradient-text italic">every baseline</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-3 max-w-lg text-slate-500">
            An 8B model trained with GRPO curriculum outperforms the 70B NIM baseline by 15–19 percentage points — at 8.75× smaller size.
          </motion.p>
        </motion.div>

        {/* Callout numbers */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={viewportOnce}
          className="mb-10 grid grid-cols-3 gap-4">
          {[
            { n: "90%", sub: "correct escalation on hard task (41→78%)" },
            { n: "85%", sub: "SLA compliance gain on full hierarchy" },
            { n: "118%", sub: "Hinglish comprehension improvement" },
          ].map(({ n, sub }) => (
            <motion.div key={n} variants={fadeUp} className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-center">
              <div className="gradient-text text-3xl font-bold">+{n}</div>
              <div className="mt-1.5 text-xs text-slate-500">{sub}</div>
            </motion.div>
          ))}
        </motion.div>

        {/* Table */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={viewportOnce}
          className="overflow-hidden rounded-2xl border border-slate-200 shadow-sm">
          <div className="grid grid-cols-[1fr_150px_150px_80px] border-b border-slate-200 bg-slate-50 px-5 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            <span>Task</span>
            <span>NIM 70B Baseline</span>
            <span>Ours (8B + GRPO)</span>
            <span>Δ</span>
          </div>
          {RESULTS.map(({ task, baseline, ours, delta }, i) => (
            <motion.div key={task} variants={fadeUp}
              className={`grid grid-cols-[1fr_150px_150px_80px] items-center px-5 py-3.5 transition-colors hover:bg-slate-50 ${i < RESULTS.length - 1 ? "border-b border-slate-100" : ""}`}>
              <span className="font-mono text-xs text-slate-700">{task}</span>
              <Bar value={baseline} color="bg-slate-300" />
              <Bar value={ours} color="bg-gradient-to-r from-indigo-500 to-violet-500" />
              <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-600">
                <TrendingUp className="h-3 w-3" />{delta}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
