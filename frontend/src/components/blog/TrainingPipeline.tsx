"use client";
import { motion } from "framer-motion";
import { Database, Cpu, BarChart2, FlaskConical, Rocket } from "lucide-react";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const STAGES = [
  {
    num: "01",
    icon: Database,
    title: "Environment Build",
    color: "indigo",
    items: ["Ticket store with 50+ categories", "LLM judge (8 reward dimensions)", "Policy engine with authority levels"],
  },
  {
    num: "02",
    icon: FlaskConical,
    title: "SFT Warm-start",
    color: "violet",
    items: ["Curated demonstration data", "Role-specific instruction tuning", "Policy-aware response seeding"],
  },
  {
    num: "03",
    icon: Cpu,
    title: "GRPO Training",
    color: "cyan",
    items: ["Group relative policy optimization", "Per-step reward accumulation", "Curriculum difficulty progression"],
  },
  {
    num: "04",
    icon: BarChart2,
    title: "Evaluation",
    color: "amber",
    items: ["Multi-domain benchmark suite", "GPT-4 and Claude baselines", "Human preference labeling"],
  },
  {
    num: "05",
    icon: Rocket,
    title: "Deployment",
    color: "emerald",
    items: ["LoRA merge to full weights", "Async 3-agent inference server", "Live demo with human-in-the-loop"],
  },
];

const colorMap: Record<string, { text: string; bg: string; border: string; dot: string }> = {
  indigo: { text: "text-indigo-600", bg: "bg-indigo-50", border: "border-indigo-200", dot: "bg-indigo-500" },
  violet: { text: "text-violet-600", bg: "bg-violet-50", border: "border-violet-200", dot: "bg-violet-500" },
  cyan:   { text: "text-cyan-600",   bg: "bg-cyan-50",   border: "border-cyan-200",   dot: "bg-cyan-500" },
  amber:  { text: "text-amber-600",  bg: "bg-amber-50",  border: "border-amber-200",  dot: "bg-amber-500" },
  emerald:{ text: "text-emerald-600",bg: "bg-emerald-50",border: "border-emerald-200",dot: "bg-emerald-500" },
};

export function TrainingPipeline() {
  return (
    <section id="pipeline" className="relative overflow-hidden bg-slate-50 py-24 md:py-36">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 bottom-0 -translate-x-1/2 h-[400px] w-[800px] rounded-full bg-cyan-100/40 blur-[120px]" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mb-16 text-center"
        >
          <motion.span variants={fadeUp} className="mb-3 inline-block text-xs font-semibold uppercase tracking-widest text-cyan-600">
            Training Pipeline
          </motion.span>
          <motion.h2
            variants={fadeUp}
            className="text-4xl font-bold text-slate-900 md:text-5xl"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
          >
            From scratch to{" "}
            <span className="gradient-text italic">state-of-the-art</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-4 max-w-xl text-slate-500">
            Five carefully sequenced stages — each building on the last — to produce a
            fully-trained multi-agent system from raw base models.
          </motion.p>
        </motion.div>

        {/* Pipeline stages */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="relative"
        >
          {/* Connecting line */}
          <div className="absolute left-6 top-8 bottom-8 w-px bg-gradient-to-b from-indigo-400 via-violet-400 via-cyan-400 via-amber-400 to-emerald-400 opacity-40 md:left-1/2" />

          <div className="space-y-6">
            {STAGES.map(({ num, icon: Icon, title, color, items }, i) => {
              const c = colorMap[color];
              const isRight = i % 2 === 1;
              return (
                <motion.div
                  key={num}
                  variants={fadeUp}
                  className={`relative flex gap-6 md:gap-0 ${isRight ? "md:flex-row-reverse" : ""}`}
                >
                  {/* Card */}
                  <div className={`w-full rounded-2xl border ${c.border} ${c.bg} bg-white p-6 shadow-sm md:w-5/12 ${isRight ? "md:ml-auto" : ""}`}>
                    <div className="flex items-start gap-4">
                      <div className={`rounded-xl border ${c.border} bg-white p-2.5 shadow-sm`}>
                        <Icon className={`h-5 w-5 ${c.text}`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className={`font-mono text-xs font-bold ${c.text}`}>{num}</span>
                          <h3 className={`text-base font-bold text-slate-900`}>{title}</h3>
                        </div>
                        <ul className="space-y-1.5">
                          {items.map((item) => (
                            <li key={item} className="flex items-center gap-2 text-xs text-slate-600">
                              <div className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>

                  {/* Center dot */}
                  <div className="hidden md:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 items-center justify-center">
                    <div className={`h-5 w-5 rounded-full border-2 border-white shadow-md ${c.dot}`} />
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
