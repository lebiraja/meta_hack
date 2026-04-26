"use client";
import { motion } from "framer-motion";
import Image from "next/image";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const PLOTS = [
  {
    src: "/plot_reward.png",
    title: "Reward",
    desc: "Baseline 0.136 → best eval 0.152. Final reward 0.240 at step 40.",
  },
  {
    src: "/plot_loss.png",
    title: "Loss",
    desc: "Stays stable throughout. No divergence or collapse.",
  },
  {
    src: "/plot_lr.png",
    title: "Learning Rate",
    desc: "Cosine annealing: 5e-5 → 5e-6 over 40 steps.",
  },
  {
    src: "/plot_invalid_rate.png",
    title: "Invalid Rate",
    desc: "Mean 0.6% — well below 90% collapse threshold.",
  },
  {
    src: "/plot_eval_scores.png",
    title: "Eval Scores",
    desc: "Best checkpoint 0.152 at step 20 vs baseline 0.136.",
  },
  {
    src: "/plot_before_after.png",
    title: "Before vs After",
    desc: "Trained (green) beats baseline (red) every eval episode.",
  },
];

export function TrainingPlots() {
  return (
    <section id="training-plots" className="bg-slate-50 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">

        {/* Header */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={viewportOnce} className="mb-12 text-center">
          <motion.span variants={fadeUp} className="text-xs font-semibold uppercase tracking-widest text-indigo-600">
            Training Curves
          </motion.span>
          <motion.h2 variants={fadeUp} className="mt-2 text-4xl font-bold text-slate-900 md:text-5xl" style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}>
            Real GRPO run —{" "}
            <span className="gradient-text italic">40 steps logged</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-3 max-w-xl text-slate-500 text-sm">
            Qwen2.5-1.5B · Colab T4 · 40 steps · curriculum_basic · 0.6% mean invalid
          </motion.p>
        </motion.div>

        {/* 2-col grid */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={viewportOnce}
          className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {PLOTS.map(({ src, title, desc }) => (
            <motion.div key={title} variants={fadeUp}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5">
              <div className="border-b border-slate-100 bg-slate-50 p-2">
                <Image src={src} alt={title} width={560} height={360} className="w-full rounded-lg object-contain" style={{ maxHeight: 180 }} />
              </div>
              <div className="px-4 py-3">
                <div className="text-sm font-bold text-slate-900">{title}</div>
                <div className="mt-0.5 text-xs text-slate-500">{desc}</div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* L40S note */}
        <motion.p variants={fadeUp} initial="hidden" whileInView="visible" viewport={viewportOnce}
          className="mt-6 text-center text-xs text-slate-400">
          Full L40S run (Llama-3.1-8B, 150 steps): reward reached <strong className="text-slate-600">0.709</strong> with <code className="rounded bg-slate-100 px-1">final=1.000</code> episodes on curriculum_supervisor · Best checkpoint: 0.531 @ step 40
        </motion.p>
      </div>
    </section>
  );
}
