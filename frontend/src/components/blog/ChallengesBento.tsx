"use client";
import { motion } from "framer-motion";
import { Zap, Lock, Brain, Target, Shuffle } from "lucide-react";
import { BentoGrid, BentoCard } from "@/components/magicui/bento-grid";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const CHALLENGES = [
  {
    icon: Brain,
    title: "Reward Shaping Without Ground Truth",
    desc: "Real support quality is subjective. We built an LLM judge that scores responses on 8 orthogonal dimensions — resolution, policy compliance, tone, efficiency — and combined them into a single GRPO training signal.",
    color: "text-indigo-600",
    bg: "from-indigo-50/80 to-transparent",
    colSpan: 2 as const,
  },
  {
    icon: Lock,
    title: "Policy Enforcement",
    desc: "Agents must internalize authority limits, not just follow rules. We encode policy constraints directly into the environment state and penalize violations harshly.",
    color: "text-violet-600",
    bg: "from-violet-50/80 to-transparent",
    colSpan: 1 as const,
  },
  {
    icon: Shuffle,
    title: "Multi-Agent Credit Assignment",
    desc: "With 3 agents acting sequentially, attributing reward to the right action is hard. We use per-step reward accumulation and agent-specific critic heads.",
    color: "text-cyan-600",
    bg: "from-cyan-50/80 to-transparent",
    colSpan: 1 as const,
  },
  {
    icon: Target,
    title: "Curriculum Design",
    desc: "We trained across 5 difficulty levels — from simple refund requests to nightmare VIP escalations — progressively expanding the action space as the agent mastered each tier.",
    color: "text-amber-600",
    bg: "from-amber-50/80 to-transparent",
    colSpan: 1 as const,
  },
  {
    icon: Zap,
    title: "Inference Latency at Demo Time",
    desc: "A 3-agent system calling an LLM three times per step was too slow. We built async parallel inference with a shared context cache, cutting step latency from 6s to under 1s.",
    color: "text-emerald-600",
    bg: "from-emerald-50/80 to-transparent",
    colSpan: 1 as const,
  },
];

export function ChallengesBento() {
  return (
    <section id="challenges" className="relative overflow-hidden bg-white py-24 md:py-36">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute right-0 bottom-0 h-[500px] w-[500px] rounded-full bg-violet-100/40 blur-[120px]" />
        <div className="absolute left-0 top-0 h-[400px] w-[400px] rounded-full bg-cyan-100/30 blur-[100px]" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mb-16 text-center"
        >
          <motion.span variants={fadeUp} className="mb-3 inline-block text-xs font-semibold uppercase tracking-widest text-violet-600">
            Research Challenges
          </motion.span>
          <motion.h2
            variants={fadeUp}
            className="text-4xl font-bold text-slate-900 md:text-5xl"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
          >
            Five hard problems we{" "}
            <span className="gradient-text italic">actually solved</span>
          </motion.h2>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
        >
          <BentoGrid>
            {CHALLENGES.map(({ icon: Icon, title, desc, color, bg, colSpan }) => (
              <motion.div key={title} variants={fadeUp}>
                <BentoCard colSpan={colSpan} className="min-h-[180px] border-slate-200 bg-white shadow-sm hover:shadow-md">
                  <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${bg} rounded-2xl`} />
                  <Icon className={`mb-4 h-7 w-7 ${color}`} />
                  <h3 className={`mb-2 text-lg font-bold ${color}`}>{title}</h3>
                  <p className="text-sm leading-relaxed text-slate-600">{desc}</p>
                </BentoCard>
              </motion.div>
            ))}
          </BentoGrid>
        </motion.div>
      </div>
    </section>
  );
}
