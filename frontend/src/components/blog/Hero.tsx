"use client";
import { motion } from "framer-motion";
import Image from "next/image";
import { ArrowRight, ChevronDown, Zap, Award, Layers, GitBranch } from "lucide-react";
import { DotPattern } from "@/components/magicui/dot-pattern";
import { ShimmerButton } from "@/components/magicui/shimmer-button";
import { NumberTicker } from "@/components/magicui/number-ticker";
import { HERO_IMAGE } from "@/lib/unsplash";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";
import Link from "next/link";

const METRICS = [
  { value: 17, prefix: "+", suffix: "pp", label: "vs GPT-4 Baseline", icon: Award, color: "text-emerald-600" },
  { value: 875, prefix: "", suffix: "×", label: "Token Efficiency", icon: Zap, color: "text-amber-600" },
  { value: 3, prefix: "", suffix: "-Level", label: "Agent Hierarchy", icon: Layers, color: "text-indigo-600" },
  { value: 5, prefix: "", suffix: " Stages", label: "Training Pipeline", icon: GitBranch, color: "text-violet-600" },
];

const HEADLINE = ["Teaching", "AI", "to", "Actually", "Support", "Customers"];

export function Hero() {
  return (
    <section
      id="hero"
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-slate-50 via-white to-white"
    >
      {/* Background image — very subtle on white */}
      <div className="absolute inset-0">
        <Image
          src={HERO_IMAGE.url}
          alt={HERO_IMAGE.alt}
          fill
          priority
          className="object-cover opacity-[0.06]"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-white/50 via-white/70 to-white" />
      </div>

      {/* Dot grid */}
      <DotPattern
        cx={1}
        cy={1}
        cr={1}
        className="[mask-image:radial-gradient(700px_circle_at_center,white,transparent)] fill-slate-900/[0.04]"
      />

      {/* Radial gradient glows — soft on white */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/3 -translate-x-1/2 -translate-y-1/2 h-[600px] w-[600px] rounded-full bg-indigo-200/40 blur-[120px]" />
        <div className="absolute left-1/4 top-2/3 h-[400px] w-[400px] rounded-full bg-violet-200/30 blur-[100px]" />
        <div className="absolute right-1/4 top-1/4 h-[300px] w-[300px] rounded-full bg-cyan-200/20 blur-[80px]" />
      </div>

      {/* Content */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="relative z-10 flex flex-col items-center px-6 text-center"
      >
        {/* Badge */}
        <motion.div variants={fadeUp} className="mb-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-indigo-600">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Technical Report · April 2026
          </span>
        </motion.div>

        {/* Headline */}
        <h1 className="mb-6 flex flex-wrap justify-center gap-x-4 gap-y-2">
          {HEADLINE.map((word, i) => (
            <motion.span
              key={i}
              initial={{ opacity: 0, y: 40, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ delay: 0.1 + i * 0.08, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              className={
                i === 4
                  ? "gradient-text text-5xl font-bold leading-tight md:text-7xl lg:text-8xl"
                  : "text-5xl font-bold leading-tight text-slate-900 md:text-7xl lg:text-8xl"
              }
              style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
            >
              {word}
            </motion.span>
          ))}
        </h1>

        {/* Subtitle */}
        <motion.p
          variants={fadeUp}
          className="mb-10 max-w-2xl text-base text-slate-500 md:text-lg"
        >
          We built a 3-level hierarchical multi-agent system — support agent, supervisor, and
          manager — trained end-to-end with GRPO to handle real customer tickets, policy
          enforcement, and escalation decisions.
        </motion.p>

        {/* CTAs */}
        <motion.div variants={fadeUp} className="mb-16 flex flex-wrap justify-center gap-3">
          <Link href="/demo">
            <ShimmerButton className="gap-2">
              Try the Live Demo <ArrowRight className="h-4 w-4" />
            </ShimmerButton>
          </Link>
          <a
            href="https://github.com/lebiraja/meta_hack"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-6 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
          >
            Source Code
          </a>
          <a
            href="https://huggingface.co/spaces/lebiraja/customer-support-env"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-6 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
          >
            HF Space
          </a>
        </motion.div>

        {/* Metrics */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="grid w-full max-w-3xl grid-cols-2 gap-4 md:grid-cols-4"
        >
          {METRICS.map(({ value, prefix, suffix, label, icon: Icon, color }) => (
            <motion.div
              key={label}
              variants={fadeUp}
              className="rounded-2xl border border-slate-200 bg-white p-4 text-center shadow-sm transition-all hover:shadow-md hover:scale-105"
            >
              <Icon className={`mx-auto mb-2 h-5 w-5 ${color}`} />
              <div className={`text-2xl font-bold tabular-nums ${color}`}>
                <NumberTicker value={value} prefix={prefix} suffix={suffix} />
              </div>
              <div className="mt-1 text-xs text-slate-500">{label}</div>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>

      {/* Scroll cue */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5, duration: 0.6 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <a href="#pain" className="flex flex-col items-center gap-1 text-slate-400 hover:text-slate-600 transition-colors">
          <span className="text-xs tracking-widest uppercase">Scroll</span>
          <ChevronDown className="h-4 w-4 animate-bounce" />
        </a>
      </motion.div>
    </section>
  );
}
