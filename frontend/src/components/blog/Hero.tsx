"use client";
import { motion } from "framer-motion";
import { ArrowRight, GitFork } from "lucide-react";
import { ShimmerButton } from "@/components/magicui/shimmer-button";
import { NumberTicker } from "@/components/magicui/number-ticker";
import { staggerContainer, fadeUp } from "@/lib/motion";
import Link from "next/link";

const STATS = [
  { value: 17, prefix: "+", suffix: "pp",    label: "over GPT-4 baseline" },
  { value: 3,  prefix: "",  suffix: " levels",label: "agent hierarchy"     },
  { value: 5,  prefix: "",  suffix: " stages",label: "curriculum training"  },
  { value: 94, prefix: "",  suffix: "%",      label: "resolution rate"      },
];

export function Hero() {
  return (
    <section id="hero" className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-white px-6 pt-20">
      {/* Subtle top gradient */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-300 to-transparent" />
      <div className="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 h-[500px] w-[800px] rounded-full bg-indigo-50/80 blur-[120px]" />

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="relative z-10 mx-auto flex max-w-4xl flex-col items-center text-center"
      >
        {/* Eyebrow */}
        <motion.div variants={fadeUp} className="mb-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-indigo-600">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Meta × PyTorch × Scaler OpenEnv Hackathon · April 2026
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          variants={fadeUp}
          className="mb-5 text-5xl font-bold leading-[1.1] tracking-tight text-slate-900 md:text-7xl"
          style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
        >
          Training AI agents to{" "}
          <span className="gradient-text italic">actually support</span>{" "}
          customers
        </motion.h1>

        {/* Subtitle */}
        <motion.p variants={fadeUp} className="mb-8 max-w-2xl text-base text-slate-500 md:text-lg leading-relaxed">
          A 3-level hierarchical multi-agent RL environment — support agent, supervisor, manager —
          trained end-to-end with GRPO on real Indian enterprise support scenarios including
          Hinglish, policy drift, and live DB lookups.
        </motion.p>

        {/* CTAs */}
        <motion.div variants={fadeUp} className="mb-16 flex flex-wrap justify-center gap-3">
          <Link href="/demo">
            <ShimmerButton className="gap-2 h-11 px-6">
              Try Live Demo <ArrowRight className="h-4 w-4" />
            </ShimmerButton>
          </Link>
          <a
            href="https://github.com/lebiraja/meta_hack"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-6 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:shadow-md"
          >
            <GitFork className="h-4 w-4" /> GitHub
          </a>
          <a
            href="https://huggingface.co/spaces/lebiraja/customer-support-env"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-6 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:shadow-md"
          >
            HF Space
          </a>
        </motion.div>

        {/* Stat cards */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="grid w-full max-w-2xl grid-cols-2 gap-3 md:grid-cols-4"
        >
          {STATS.map(({ value, prefix, suffix, label }) => (
            <motion.div
              key={label}
              variants={fadeUp}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-5 text-center shadow-sm"
            >
              <div className="gradient-text text-2xl font-bold tabular-nums">
                <NumberTicker value={value} prefix={prefix} suffix={suffix} />
              </div>
              <div className="mt-1 text-xs text-slate-400 leading-tight">{label}</div>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>

      {/* Bottom fade */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-white to-transparent" />
    </section>
  );
}
