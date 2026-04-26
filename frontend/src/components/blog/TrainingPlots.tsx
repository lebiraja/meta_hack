"use client";
import { motion } from "framer-motion";
import Image from "next/image";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const PLOTS = [
  {
    src: "/plot_reward.png",
    title: "Reward Curve",
    desc: "Mean group reward per step — raw (faint) + smoothed trend. Baseline 0.136 → best eval 0.152. Final reward 0.240 at step 40.",
    badge: "+8% improvement",
    badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  {
    src: "/plot_loss.png",
    title: "GRPO Loss",
    desc: "Loss stays stable throughout 40 steps. No collapse. Brief dip at step 5 (exploration) then plateaus — a healthy GRPO training signal.",
    badge: "Stable",
    badgeColor: "bg-indigo-50 text-indigo-700 border-indigo-200",
  },
  {
    src: "/plot_lr.png",
    title: "Learning Rate Schedule",
    desc: "Clean cosine annealing from 5e-5 → 5e-6. Gradual decay prevents overshooting and keeps the model from forgetting earlier learned behaviour.",
    badge: "Cosine annealing",
    badgeColor: "bg-violet-50 text-violet-700 border-violet-200",
  },
  {
    src: "/plot_invalid_rate.png",
    title: "Invalid Action Rate",
    desc: "Mean 0.6% invalid throughout — one brief spike at step 5, then near-zero. Well below the 90% collapse threshold. Zero fallbacks after step 10.",
    badge: "0.6% mean invalid",
    badgeColor: "bg-amber-50 text-amber-700 border-amber-200",
  },
  {
    src: "/plot_eval_scores.png",
    title: "Eval Score History",
    desc: "Model scored at steps 10, 20, 30, 40. Best checkpoint 0.152 at step 20. Baseline 0.136. The trained model consistently outperforms the untrained baseline.",
    badge: "Best: 0.152",
    badgeColor: "bg-cyan-50 text-cyan-700 border-cyan-200",
  },
  {
    src: "/plot_before_after.png",
    title: "Before vs After",
    desc: "Episode-level score comparison — trained agent (green) consistently outscores the untrained baseline (red) across all 5 evaluation episodes.",
    badge: "Green > Red every episode",
    badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
];

export function TrainingPlots() {
  return (
    <section id="training-plots" className="relative overflow-hidden bg-white py-24 md:py-32">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-0 -translate-x-1/2 h-[400px] w-[800px] rounded-full bg-indigo-100/30 blur-[120px]" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mb-16 text-center"
        >
          <motion.span variants={fadeUp} className="mb-3 inline-block text-xs font-semibold uppercase tracking-widest text-indigo-600">
            Training Curves
          </motion.span>
          <motion.h2
            variants={fadeUp}
            className="text-4xl font-bold text-slate-900 md:text-5xl"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
          >
            Real GRPO run —{" "}
            <span className="gradient-text italic">every step logged</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-4 max-w-2xl text-slate-500">
            Qwen2.5-1.5B on Colab T4 · 40 steps · curriculum_basic · baseline 0.136 → best eval 0.152 (+8%) · 0.6% mean invalid rate
          </motion.p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
        >
          {PLOTS.map(({ src, title, desc, badge, badgeColor }) => (
            <motion.div
              key={title}
              variants={fadeUp}
              className="group overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-all duration-300 hover:shadow-lg hover:-translate-y-1"
            >
              <div className="relative overflow-hidden bg-slate-50 border-b border-slate-100">
                <Image
                  src={src}
                  alt={title}
                  width={600}
                  height={400}
                  className="w-full object-contain"
                  style={{ maxHeight: "200px" }}
                />
              </div>
              <div className="p-4">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="text-sm font-bold text-slate-900">{title}</h3>
                  <span className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${badgeColor}`}>
                    {badge}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-slate-500">{desc}</p>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* L40S note */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mt-8 rounded-2xl border border-indigo-100 bg-indigo-50 p-5"
        >
          <p className="text-sm text-indigo-800">
            <span className="font-semibold">Full run (L40S A100 · 150 steps · Llama-3.1-8B):</span>{" "}
            Model auto-advanced through curriculum stages basic → supervisor → full_hierarchy. Reward reached <strong>0.709</strong> with <code className="rounded bg-indigo-100 px-1 text-xs">final=1.000</code> episodes on curriculum_supervisor by step 90. Best checkpoint score: 0.531 at step 40.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
