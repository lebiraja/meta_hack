"use client";
import { motion } from "framer-motion";
import { User, Shield, Crown, ArrowRight, MessageSquare, FileText, CheckCircle } from "lucide-react";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const LEVELS = [
  {
    id: "L1",
    icon: User,
    title: "Support Agent",
    subtitle: "Level 1",
    color: "indigo",
    bg: "bg-indigo-500/10",
    border: "border-indigo-500/30",
    iconColor: "text-indigo-400",
    gradient: "from-indigo-600 to-indigo-400",
    actions: ["Respond to customer", "Query ticket store", "Issue refund (≤$50)", "Escalate to L2"],
    desc: "Front-line agent handling standard queries, operating within policy constraints.",
  },
  {
    id: "L2",
    icon: Shield,
    title: "Supervisor",
    subtitle: "Level 2",
    color: "violet",
    bg: "bg-violet-500/10",
    border: "border-violet-500/30",
    iconColor: "text-violet-400",
    gradient: "from-violet-600 to-violet-400",
    actions: ["Override L1 decisions", "Adjust refund limit", "Issue directives", "Escalate to L3"],
    desc: "Reviews escalated tickets and adjusts policy for active sessions.",
  },
  {
    id: "L3",
    icon: Crown,
    title: "Manager",
    subtitle: "Level 3",
    color: "amber",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    iconColor: "text-amber-400",
    gradient: "from-amber-600 to-amber-400",
    actions: ["Set global policy", "Approve large refunds", "Handle VIP tickets", "Audit decisions"],
    desc: "Ultimate authority. Sets global policy and handles only critical escalations.",
  },
];

export function ArchitectureSection() {
  return (
    <section id="architecture" className="relative overflow-hidden bg-slate-950 py-24 md:py-36">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[700px] w-[700px] rounded-full bg-indigo-900/15 blur-[140px]" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mb-16 text-center"
        >
          <motion.span variants={fadeUp} className="mb-3 inline-block text-xs font-semibold uppercase tracking-widest text-indigo-400">
            Architecture
          </motion.span>
          <motion.h2
            variants={fadeUp}
            className="text-4xl font-bold text-white md:text-5xl"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
          >
            A hierarchy that{" "}
            <span className="gradient-text italic">mirrors human orgs</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-4 max-w-2xl text-slate-400">
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
          {LEVELS.map(({ id, icon: Icon, title, subtitle, bg, border, iconColor, gradient, actions, desc }) => (
            <motion.div
              key={id}
              variants={fadeUp}
              className={`group relative overflow-hidden rounded-2xl border ${border} ${bg} p-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl`}
            >
              {/* Level badge */}
              <div className={`mb-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-r ${gradient} px-3 py-1`}>
                <Icon className="h-3.5 w-3.5 text-white" />
                <span className="text-xs font-bold text-white">{subtitle}</span>
              </div>

              <h3 className={`mb-2 text-xl font-bold ${iconColor}`}>{title}</h3>
              <p className="mb-4 text-sm text-slate-400 leading-relaxed">{desc}</p>

              <div className="space-y-2">
                {actions.map((action) => (
                  <div key={action} className="flex items-center gap-2 text-xs text-slate-400">
                    <CheckCircle className={`h-3 w-3 shrink-0 ${iconColor}`} />
                    {action}
                  </div>
                ))}
              </div>

              {/* Decorative gradient */}
              <div className={`pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-gradient-to-br ${gradient} opacity-10 blur-2xl`} />
            </motion.div>
          ))}
        </motion.div>

        {/* Flow diagram */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mt-16 glass rounded-3xl p-8"
        >
          <motion.h3 variants={fadeUp} className="mb-8 text-center text-lg font-semibold text-slate-300">
            Request Flow
          </motion.h3>
          <div className="flex flex-wrap items-center justify-center gap-3">
            {[
              { icon: MessageSquare, label: "Customer Message", color: "text-slate-400" },
              null,
              { icon: User, label: "L1 Support Agent", color: "text-indigo-400" },
              null,
              { icon: Shield, label: "L2 Supervisor", color: "text-violet-400" },
              null,
              { icon: Crown, label: "L3 Manager", color: "text-amber-400" },
              null,
              { icon: CheckCircle, label: "Resolved", color: "text-emerald-400" },
              null,
              { icon: FileText, label: "Reward Signal", color: "text-cyan-400" },
            ].map((item, i) =>
              item === null ? (
                <ArrowRight key={i} className="h-4 w-4 text-slate-600" />
              ) : (
                <motion.div
                  key={item.label}
                  variants={fadeUp}
                  className="flex flex-col items-center gap-2"
                >
                  <div className={`glass rounded-xl p-3`}>
                    <item.icon className={`h-5 w-5 ${item.color}`} />
                  </div>
                  <span className="text-xs text-slate-500">{item.label}</span>
                </motion.div>
              )
            )}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
