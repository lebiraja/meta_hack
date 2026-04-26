"use client";
import { motion } from "framer-motion";
import { ArrowRight, Play, GitFork } from "lucide-react";
import { ShimmerButton } from "@/components/magicui/shimmer-button";
import { DotPattern } from "@/components/magicui/dot-pattern";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";
import Link from "next/link";

export function CallToAction() {
  return (
    <section id="cta" className="relative overflow-hidden bg-gradient-to-br from-indigo-600 via-violet-600 to-indigo-700 py-24 md:py-36">
      <DotPattern className="[mask-image:radial-gradient(600px_circle_at_center,white,transparent)] fill-white/[0.05]" />

      {/* Glows */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full bg-white/5 blur-[100px]" />
        <div className="absolute left-1/4 top-1/4 h-[300px] w-[300px] rounded-full bg-cyan-400/10 blur-[80px]" />
      </div>

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
        className="relative mx-auto max-w-3xl px-6 text-center"
      >
        <motion.div variants={fadeUp} className="mb-4">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-white">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live Demo Available
          </span>
        </motion.div>

        <motion.h2
          variants={fadeUp}
          className="mb-4 text-4xl font-bold text-white md:text-6xl"
          style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
        >
          See the agents{" "}
          <span className="italic text-indigo-200">in action</span>
        </motion.h2>

        <motion.p variants={fadeUp} className="mb-10 text-base text-indigo-200 leading-relaxed">
          Watch the 3-level hierarchy handle real customer tickets — including edge cases,
          policy overrides, and escalations — in our live interactive demo.
        </motion.p>

        <motion.div variants={fadeUp} className="flex flex-wrap justify-center gap-4">
          <Link href="/demo">
            <ShimmerButton className="gap-2 text-base px-8 h-12 border border-white/20">
              <Play className="h-4 w-4" fill="white" />
              Try the Demo
            </ShimmerButton>
          </Link>
          <a
            href="https://github.com/lebiraja/meta_hack"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-12 items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-8 text-base font-semibold text-white backdrop-blur-sm transition-all hover:bg-white/20"
          >
            <GitFork className="h-4 w-4" />
            GitHub
          </a>
          <Link
            href="/dashboard"
            className="inline-flex h-12 items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-8 text-base font-semibold text-white backdrop-blur-sm transition-all hover:bg-white/20"
          >
            Dashboard
            <ArrowRight className="h-4 w-4" />
          </Link>
        </motion.div>
      </motion.div>
    </section>
  );
}
