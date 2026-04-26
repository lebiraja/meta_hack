"use client";
import { motion } from "framer-motion";
import { User, Shield, Crown, CheckCircle, ArrowRight } from "lucide-react";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const LEVELS = [
  {
    id: "L1", icon: User, title: "Support Agent",
    color: "indigo", border: "border-indigo-200", bg: "bg-indigo-50",
    badge: "bg-indigo-600", iconColor: "text-indigo-600",
    actions: ["Respond & info-gather", "Query live order DB", "Issue refund ≤ ₹500", "Escalate to L2"],
    reward: "Empathy 30% · Accuracy 25% · Resolution 25% · Efficiency 20%",
  },
  {
    id: "L2", icon: Shield, title: "Supervisor",
    color: "violet", border: "border-violet-200", bg: "bg-violet-50",
    badge: "bg-violet-600", iconColor: "text-violet-600",
    actions: ["Approve or reject L1 action", "Give corrective feedback", "Adjust refund ceiling", "Escalate to L3"],
    reward: "Oversight quality 35% · Escalation fit 30% · Policy 20%",
  },
  {
    id: "L3", icon: Crown, title: "Manager",
    color: "amber", border: "border-amber-200", bg: "bg-amber-50",
    badge: "bg-amber-600", iconColor: "text-amber-600",
    actions: ["Final policy authority", "Approve large refunds", "Override L2 decisions", "Resolve VIP tickets"],
    reward: "Decision quality 45% · Resolution 30% · Decisiveness 25%",
  },
];

const FLOW = [
  { label: "Customer", icon: "💬", sub: "Opens ticket" },
  { label: "L1 Agent",  icon: "🤝", sub: "Responds & queries DB" },
  { label: "L2 Review", icon: "🔍", sub: "Approve / reject / escalate" },
  { label: "L3 Manager",icon: "👑", sub: "Final authority if needed" },
  { label: "Resolved",  icon: "✅", sub: "Reward computed → GRPO" },
];

export function ArchitectureSection() {
  return (
    <section id="architecture" className="bg-slate-50 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">

        {/* Header */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={viewportOnce} className="mb-14 text-center">
          <motion.span variants={fadeUp} className="text-xs font-semibold uppercase tracking-widest text-indigo-600">
            Architecture
          </motion.span>
          <motion.h2 variants={fadeUp} className="mt-2 text-4xl font-bold text-slate-900 md:text-5xl" style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}>
            3-level hierarchy that{" "}
            <span className="gradient-text italic">mirrors human orgs</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-4 max-w-xl text-slate-500">
            Every L1 action is held pending until L2 reviews it. Agents can't skip the loop. Authority is enforced, not optional.
          </motion.p>
        </motion.div>

        {/* Agent cards */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={viewportOnce} className="mb-10 grid gap-5 md:grid-cols-3">
          {LEVELS.map(({ id, icon: Icon, title, border, bg, badge, iconColor, actions, reward }) => (
            <motion.div key={id} variants={fadeUp} className={`rounded-2xl border ${border} ${bg} p-5`}>
              <div className="mb-3 flex items-center gap-2">
                <span className={`inline-flex items-center justify-center rounded-full ${badge} p-1.5`}>
                  <Icon className="h-3.5 w-3.5 text-white" />
                </span>
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">{id}</span>
                <span className={`ml-auto text-sm font-bold ${iconColor}`}>{title}</span>
              </div>
              <ul className="mb-3 space-y-1.5">
                {actions.map(a => (
                  <li key={a} className="flex items-center gap-2 text-xs text-slate-600">
                    <CheckCircle className={`h-3 w-3 shrink-0 ${iconColor}`} />{a}
                  </li>
                ))}
              </ul>
              <p className={`text-[10px] leading-relaxed ${iconColor} opacity-80`}>{reward}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* Flow strip */}
        <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={viewportOnce}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-center gap-2">
            {FLOW.map((step, i) => (
              <div key={step.label} className="flex items-center gap-2">
                <div className="flex flex-col items-center gap-1 text-center">
                  <span className="text-xl">{step.icon}</span>
                  <span className="text-xs font-semibold text-slate-800">{step.label}</span>
                  <span className="text-[10px] text-slate-400 max-w-[80px] leading-tight">{step.sub}</span>
                </div>
                {i < FLOW.length - 1 && <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-300" />}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
