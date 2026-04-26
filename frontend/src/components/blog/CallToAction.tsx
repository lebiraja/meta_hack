"use client";
import { motion } from "framer-motion";
import Image from "next/image";
import { ArrowRight, Play, GitFork } from "lucide-react";
import { ShimmerButton } from "@/components/magicui/shimmer-button";
import { DotPattern } from "@/components/magicui/dot-pattern";
import { CTA_IMAGE } from "@/lib/unsplash";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";
import Link from "next/link";

export function CallToAction() {
  return (
    <section id="cta" className="relative overflow-hidden bg-slate-950 py-24 md:py-36">
      {/* Background image */}
      <div className="absolute inset-0">
        <Image
          src={CTA_IMAGE.url}
          alt={CTA_IMAGE.alt}
          fill
          className="object-cover opacity-5"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-slate-950 via-slate-950/95 to-slate-950" />
      </div>

      <DotPattern className="[mask-image:radial-gradient(500px_circle_at_center,white,transparent)] fill-white/[0.02]" />

      {/* Glows */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[600px] w-[600px] rounded-full bg-indigo-600/15 blur-[120px]" />
        <div className="absolute left-1/3 top-1/4 h-[300px] w-[300px] rounded-full bg-violet-700/10 blur-[80px]" />
        <div className="absolute right-1/4 bottom-1/4 h-[200px] w-[200px] rounded-full bg-cyan-600/10 blur-[60px]" />
      </div>

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
        className="relative mx-auto max-w-3xl px-6 text-center"
      >
        <motion.div variants={fadeUp} className="mb-4">
          <span className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-indigo-300">
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
          <span className="gradient-text italic">in action</span>
        </motion.h2>

        <motion.p variants={fadeUp} className="mb-10 text-base text-slate-400 leading-relaxed">
          Watch the 3-level hierarchy handle real customer tickets — including edge cases,
          policy overrides, and escalations — in our live interactive demo.
        </motion.p>

        <motion.div variants={fadeUp} className="flex flex-wrap justify-center gap-4">
          <Link href="/demo">
            <ShimmerButton className="gap-2 text-base px-8 h-12">
              <Play className="h-4 w-4" fill="white" />
              Try the Demo
            </ShimmerButton>
          </Link>
          <a
            href="https://github.com/lebiraja/meta_hack"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-12 items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-8 text-base font-semibold text-slate-200 backdrop-blur-sm transition-all hover:border-white/25 hover:bg-white/10 hover:text-white"
          >
            <GitFork className="h-4 w-4" />
            GitHub
          </a>
          <Link
            href="/dashboard"
            className="inline-flex h-12 items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-8 text-base font-semibold text-slate-200 backdrop-blur-sm transition-all hover:border-white/25 hover:bg-white/10 hover:text-white"
          >
            Dashboard
            <ArrowRight className="h-4 w-4" />
          </Link>
        </motion.div>
      </motion.div>
    </section>
  );
}
