"use client";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const RESULTS = [
  { task: "Standard Refund Request", baseline: 71, ours: 89, delta: 18 },
  { task: "Policy Override Decision", baseline: 58, ours: 76, delta: 18 },
  { task: "Multi-turn Escalation", baseline: 49, ours: 67, delta: 18 },
  { task: "VIP Ticket Prioritization", baseline: 63, ours: 82, delta: 19 },
  { task: "Cross-channel Consistency", baseline: 55, ours: 70, delta: 15 },
  { task: "SLA Compliance", baseline: 74, ours: 88, delta: 14 },
  { task: "Nightmare Scenario (All)", baseline: 41, ours: 58, delta: 17 },
];

function DeltaBadge({ delta }: { delta: number }) {
  if (delta > 0)
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-xs font-bold text-emerald-700">
        <TrendingUp className="h-3 w-3" />+{delta}pp
      </span>
    );
  if (delta < 0)
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 border border-rose-200 px-2.5 py-0.5 text-xs font-bold text-rose-700">
        <TrendingDown className="h-3 w-3" />{delta}pp
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-500">
      <Minus className="h-3 w-3" />—
    </span>
  );
}

function ScoreBar({ value, max = 100, color }: { value: number; max?: number; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: `${(value / max) * 100}%` }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
      <span className="w-8 text-right text-xs font-semibold tabular-nums text-slate-700">{value}</span>
    </div>
  );
}

export function ResultsTable() {
  return (
    <section id="results" className="relative overflow-hidden bg-white py-24 md:py-36">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute right-0 top-1/3 h-[500px] w-[500px] rounded-full bg-emerald-100/40 blur-[120px]" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mb-16 text-center"
        >
          <motion.span variants={fadeUp} className="mb-3 inline-block text-xs font-semibold uppercase tracking-widest text-emerald-600">
            Results
          </motion.span>
          <motion.h2
            variants={fadeUp}
            className="text-4xl font-bold text-slate-900 md:text-5xl"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
          >
            +15–19pp over{" "}
            <span className="gradient-text italic">every baseline</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-4 max-w-xl text-slate-500">
            Evaluated on our multi-domain benchmark. Scores represent LLM-judge resolution quality (0–100).
          </motion.p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="overflow-hidden rounded-2xl border border-slate-200 shadow-sm"
        >
          {/* Header */}
          <div className="grid grid-cols-[1fr_160px_160px_100px] gap-4 border-b border-slate-200 bg-slate-50 px-6 py-4 text-xs font-semibold uppercase tracking-widest text-slate-500">
            <span>Task Category</span>
            <span>GPT-4 Baseline</span>
            <span>AgentOS (Ours)</span>
            <span>Delta</span>
          </div>

          {RESULTS.map(({ task, baseline, ours, delta }, i) => (
            <motion.div
              key={task}
              variants={fadeUp}
              className={`grid grid-cols-[1fr_160px_160px_100px] items-center gap-4 px-6 py-4 transition-colors hover:bg-slate-50 ${
                i < RESULTS.length - 1 ? "border-b border-slate-100" : ""
              }`}
            >
              <span className="text-sm font-medium text-slate-800">{task}</span>
              <ScoreBar value={baseline} color="bg-slate-300" />
              <ScoreBar value={ours} color="bg-gradient-to-r from-indigo-500 to-violet-500" />
              <DeltaBadge delta={delta} />
            </motion.div>
          ))}

          {/* Footer avg */}
          <div className="grid grid-cols-[1fr_160px_160px_100px] items-center gap-4 border-t border-slate-200 bg-slate-50 px-6 py-4">
            <span className="text-sm font-bold text-slate-900">Average</span>
            <ScoreBar value={59} color="bg-slate-300" />
            <ScoreBar value={76} color="bg-gradient-to-r from-indigo-500 to-emerald-500" />
            <DeltaBadge delta={17} />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
