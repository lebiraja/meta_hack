"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";

import { BlogNav } from "@/components/blog/BlogNav";
import { Hero } from "@/components/blog/Hero";
import { StatsBar } from "@/components/blog/StatsBar";
import { PainSection } from "@/components/blog/PainSection";
import { ArchitectureSection } from "@/components/blog/ArchitectureSection";
import { ChallengesBento } from "@/components/blog/ChallengesBento";
import { PullQuote } from "@/components/blog/PullQuote";
import { TrainingPipeline } from "@/components/blog/TrainingPipeline";
import { TrainingPlots } from "@/components/blog/TrainingPlots";
import { ResultsTable } from "@/components/blog/ResultsTable";
import { TestimonialMarquee } from "@/components/blog/TestimonialMarquee";
import { CallToAction } from "@/components/blog/CallToAction";
import { Footer } from "@/components/blog/Footer";
import { mdxComponents } from "@/components/blog/markdown/MdxComponents";
import { fadeUp, viewportOnce } from "@/lib/motion";

export default function BlogPage() {
  const [content, setContent] = useState<string>("");

  useEffect(() => {
    fetch("/blog.md")
      .then((r) => r.text())
      .then((text) => {
        const lines = text.split("\n");
        const firstHrIdx = lines.findIndex((l, i) => i > 0 && l.trim() === "---");
        const cleaned =
          firstHrIdx > 0
            ? lines.slice(firstHrIdx + 1).join("\n").trimStart()
            : text;
        setContent(cleaned);
      })
      .catch(() => setContent(""));
  }, []);

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <BlogNav />
      <Hero />
      <StatsBar />
      <PainSection />
      <ArchitectureSection />

      <PullQuote
        text="Real customer support is messy, hierarchical, and context-heavy. We built an AI system that finally reflects that reality."
        attribution="AgentOS Research Team"
      />

      <ChallengesBento />
      <TrainingPipeline />
      <TrainingPlots />
      <ResultsTable />
      <TestimonialMarquee />

      <PullQuote
        text="After 12,000 training episodes across 5 difficulty tiers, the agents learned not just to respond — but when to defer, when to override, and when to escalate."
      />

      {/* Deep dive article from blog.md */}
      {content && (
        <section id="article" className="relative bg-white py-24 md:py-32">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-slate-300 to-transparent" />

          <div className="mx-auto max-w-3xl px-6">
            <motion.div
              variants={fadeUp}
              initial="hidden"
              whileInView="visible"
              viewport={viewportOnce}
              className="mb-12 text-center"
            >
              <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                Full Technical Report
              </span>
              <h2
                className="mt-3 text-4xl font-bold text-slate-900"
                style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
              >
                Deep Dive
              </h2>
              <div className="mx-auto mt-4 h-px w-24 bg-gradient-to-r from-transparent via-indigo-400 to-transparent" />
            </motion.div>

            <article className="blog-prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdxComponents}>
                {content}
              </ReactMarkdown>
            </article>
          </div>
        </section>
      )}

      <CallToAction />
      <Footer />
    </div>
  );
}
