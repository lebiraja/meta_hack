"use client";
import { motion } from "framer-motion";
import Image from "next/image";
import { AlertTriangle, Clock, TrendingDown, Users } from "lucide-react";
import { PAIN_IMAGE } from "@/lib/unsplash";
import { fadeUp, slideInLeft, slideInRight, staggerContainer, viewportOnce } from "@/lib/motion";

const PAIN_POINTS = [
  { icon: Clock, label: "8–24h response times", desc: "Customers waiting hours for basic order status" },
  { icon: AlertTriangle, label: "Policy violations", desc: "Agents approving refunds above their authority level" },
  { icon: TrendingDown, label: "Inconsistent escalation", desc: "Same issue, different resolution every time" },
  { icon: Users, label: "Supervisor bottlenecks", desc: "L2/L3 overwhelmed by tickets that L1 should handle" },
];

export function PainSection() {
  return (
    <section id="pain" className="relative overflow-hidden bg-slate-950 py-24 md:py-36">
      {/* background gradient */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute right-0 top-0 h-[500px] w-[500px] rounded-full bg-rose-900/10 blur-[120px]" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6">
        <div className="grid items-center gap-16 lg:grid-cols-2">
          {/* Left: image */}
          <motion.div
            variants={slideInLeft}
            initial="hidden"
            whileInView="visible"
            viewport={viewportOnce}
            className="relative"
          >
            <div className="relative overflow-hidden rounded-3xl">
              <Image
                src={PAIN_IMAGE.url}
                alt={PAIN_IMAGE.alt}
                width={700}
                height={500}
                className="h-[400px] w-full object-cover brightness-75"
              />
              <div className="absolute inset-0 bg-gradient-to-tr from-slate-950/60 via-transparent to-rose-900/20" />
              {/* Overlay stat */}
              <div className="absolute bottom-6 left-6 right-6 glass rounded-2xl p-4">
                <div className="text-3xl font-bold text-rose-400">67%</div>
                <div className="text-sm text-slate-300">of customers cite slow response as top frustration</div>
              </div>
            </div>
          </motion.div>

          {/* Right: text */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={viewportOnce}
          >
            <motion.div variants={fadeUp} className="mb-3">
              <span className="text-xs font-semibold uppercase tracking-widest text-rose-400">
                The Problem
              </span>
            </motion.div>
            <motion.h2
              variants={fadeUp}
              className="mb-6 text-4xl font-bold leading-tight text-white md:text-5xl"
              style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
            >
              Customer support is{" "}
              <span className="italic text-rose-400">broken</span> — and AI hasn&apos;t fixed it
            </motion.h2>
            <motion.p variants={fadeUp} className="mb-8 text-base text-slate-400 leading-relaxed">
              Current LLM-based support bots are either too rigid (rule-based) or too
              unpredictable (unconstrained generation). Neither respects the real-world hierarchy
              of authority, policy constraints, and escalation logic that human teams follow.
            </motion.p>

            <motion.div variants={staggerContainer} className="grid gap-4 sm:grid-cols-2">
              {PAIN_POINTS.map(({ icon: Icon, label, desc }) => (
                <motion.div
                  key={label}
                  variants={fadeUp}
                  className="flex gap-3 rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 transition-all hover:border-rose-500/40"
                >
                  <Icon className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
                  <div>
                    <div className="text-sm font-semibold text-slate-200">{label}</div>
                    <div className="mt-1 text-xs text-slate-500">{desc}</div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
