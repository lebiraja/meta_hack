"use client";
import { motion } from "framer-motion";
import { User, Shield, Crown, CheckCircle, ArrowRight, ArrowDown, MessageSquare, FileText } from "lucide-react";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const LEVELS = [
  {
    id: "L1",
    icon: User,
    title: "Support Agent",
    subtitle: "Level 1",
    color: "indigo",
    bg: "bg-indigo-50",
    border: "border-indigo-200",
    iconColor: "text-indigo-600",
    badgeBg: "bg-indigo-600",
    actions: ["Respond to customer", "Query ticket store", "Issue refund (≤₹500)", "Escalate to L2"],
    desc: "Front-line agent handling standard queries within policy constraints.",
  },
  {
    id: "L2",
    icon: Shield,
    title: "Supervisor",
    subtitle: "Level 2",
    color: "violet",
    bg: "bg-violet-50",
    border: "border-violet-200",
    iconColor: "text-violet-600",
    badgeBg: "bg-violet-600",
    actions: ["Override L1 decisions", "Adjust refund limit", "Issue directives", "Escalate to L3"],
    desc: "Reviews escalated tickets and adjusts policy for active sessions.",
  },
  {
    id: "L3",
    icon: Crown,
    title: "Manager",
    subtitle: "Level 3",
    color: "amber",
    bg: "bg-amber-50",
    border: "border-amber-200",
    iconColor: "text-amber-600",
    badgeBg: "bg-amber-600",
    actions: ["Set global policy", "Approve large refunds", "Handle VIP tickets", "Audit decisions"],
    desc: "Ultimate authority. Sets global policy and handles critical escalations.",
  },
];

const FLOW_STEPS = [
  { icon: MessageSquare, label: "Customer", sub: "Opens ticket", color: "text-slate-600", bg: "bg-slate-100", border: "border-slate-300" },
  { icon: User, label: "L1 Agent", sub: "Responds & queries", color: "text-indigo-600", bg: "bg-indigo-50", border: "border-indigo-300" },
  { icon: Shield, label: "L2 Review", sub: "Approves or rejects", color: "text-violet-600", bg: "bg-violet-50", border: "border-violet-300" },
  { icon: Crown, label: "L3 Manager", sub: "Final authority", color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-300" },
  { icon: CheckCircle, label: "Resolved", sub: "Ticket closed", color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-300" },
  { icon: FileText, label: "Reward Signal", sub: "GRPO update", color: "text-cyan-600", bg: "bg-cyan-50", border: "border-cyan-300" },
];

export function ArchitectureSection() {
  return (
    <section id="architecture" className="relative overflow-hidden bg-slate-50 py-24 md:py-36">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[700px] w-[700px] rounded-full bg-indigo-100/40 blur-[140px]" />
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
            Architecture
          </motion.span>
          <motion.h2
            variants={fadeUp}
            className="text-4xl font-bold text-slate-900 md:text-5xl"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
          >
            A hierarchy that{" "}
            <span className="gradient-text italic">mirrors human orgs</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-4 max-w-2xl text-slate-500">
            Three independent LLM agents share a ticket context but operate at different authority
            levels. GRPO training teaches each one when to act, when to defer, and when to override.
          </motion.p>
        </motion.div>

        {/* Agent cards */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="grid gap-6 md:grid-cols-3"
        >
          {LEVELS.map(({ id, icon: Icon, title, subtitle, bg, border, iconColor, badgeBg, actions, desc }) => (
            <motion.div
              key={id}
              variants={fadeUp}
              className={`group relative overflow-hidden rounded-2xl border ${border} ${bg} p-6 transition-all duration-300 hover:shadow-lg`}
            >
              {/* Level badge */}
              <div className={`mb-4 inline-flex items-center gap-2 rounded-full ${badgeBg} px-3 py-1`}>
                <Icon className="h-3.5 w-3.5 text-white" />
                <span className="text-xs font-bold text-white">{subtitle}</span>
              </div>

              <h3 className={`mb-2 text-xl font-bold ${iconColor}`}>{title}</h3>
              <p className="mb-4 text-sm text-slate-500 leading-relaxed">{desc}</p>

              <div className="space-y-2">
                {actions.map((action) => (
                  <div key={action} className="flex items-center gap-2 text-xs text-slate-600">
                    <CheckCircle className={`h-3 w-3 shrink-0 ${iconColor}`} />
                    {action}
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Visual flow diagram */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mt-16 rounded-3xl border border-slate-200 bg-white p-8 shadow-sm"
        >
          <motion.h3 variants={fadeUp} className="mb-2 text-center text-lg font-bold text-slate-900">
            Request Flow
          </motion.h3>
          <motion.p variants={fadeUp} className="mb-8 text-center text-sm text-slate-500">
            Every customer message flows through the full hierarchy before a reward signal is computed
          </motion.p>

          {/* Mobile: vertical */}
          <div className="flex flex-col items-center gap-0 md:hidden">
            {FLOW_STEPS.map((step, i) => (
              <div key={step.label} className="flex flex-col items-center">
                <motion.div
                  variants={fadeUp}
                  className={`flex w-48 items-center gap-3 rounded-2xl border ${step.border} ${step.bg} p-3`}
                >
                  <div className={`rounded-xl border ${step.border} bg-white p-2`}>
                    <step.icon className={`h-5 w-5 ${step.color}`} />
                  </div>
                  <div>
                    <div className={`text-sm font-bold ${step.color}`}>{step.label}</div>
                    <div className="text-[10px] text-slate-400">{step.sub}</div>
                  </div>
                </motion.div>
                {i < FLOW_STEPS.length - 1 && (
                  <ArrowDown className="my-1 h-4 w-4 text-slate-300" />
                )}
              </div>
            ))}
          </div>

          {/* Desktop: horizontal */}
          <div className="hidden md:flex items-center justify-between gap-2">
            {FLOW_STEPS.map((step, i) => (
              <div key={step.label} className="flex items-center gap-2">
                <motion.div
                  variants={fadeUp}
                  className="flex flex-col items-center gap-2"
                >
                  <div className={`rounded-2xl border ${step.border} ${step.bg} p-3 flex flex-col items-center gap-1.5 min-w-[96px]`}>
                    <div className={`rounded-xl border ${step.border} bg-white p-2`}>
                      <step.icon className={`h-5 w-5 ${step.color}`} />
                    </div>
                    <span className={`text-xs font-bold ${step.color}`}>{step.label}</span>
                    <span className="text-[9px] text-slate-400 text-center leading-tight">{step.sub}</span>
                  </div>
                </motion.div>
                {i < FLOW_STEPS.length - 1 && (
                  <ArrowRight className="h-4 w-4 shrink-0 text-slate-300" />
                )}
              </div>
            ))}
          </div>

          {/* L2 review note */}
          <div className="mt-6 flex items-start gap-2 rounded-xl bg-violet-50 border border-violet-100 p-4">
            <Shield className="mt-0.5 h-4 w-4 shrink-0 text-violet-600" />
            <p className="text-xs text-slate-600">
              <span className="font-semibold text-violet-600">Supervisor review is mandatory</span> — every L1 action is held pending until L2 approves, rejects (with feedback), or escalates to L3. The agent cannot skip this loop.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
