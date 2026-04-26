"use client";
import { motion } from "framer-motion";
import { User, Shield, Crown, MessageSquare, CheckCircle, ArrowDown } from "lucide-react";
import { staggerContainer, fadeUp, viewportOnce } from "@/lib/motion";

const CONVERSATION = [
  {
    role: "Customer",
    icon: MessageSquare,
    text: "Yaar mera payment stuck hai — ₹4,999 kat gaya lekin order confirm nahi hua. Please help!",
    color: "text-slate-700",
    bg: "bg-slate-50",
    border: "border-slate-200",
    badge: "bg-slate-200 text-slate-700",
    align: "left",
    meta: null,
  },
  {
    role: "L1 Support Agent",
    icon: User,
    text: "Hello! I understand your concern about the payment. Let me look this up right away. [Queried DB → order: ORD-4821, status: payment_processing, amount: ₹4,999]",
    color: "text-indigo-700",
    bg: "bg-indigo-50",
    border: "border-indigo-200",
    badge: "bg-indigo-100 text-indigo-700",
    align: "right",
    meta: "🔍 DB query executed",
  },
  {
    role: "L2 Supervisor Review",
    icon: Shield,
    text: "✓ Approved — grounded response with correct DB data. L1 correctly greeted before querying. Proceeding.",
    color: "text-violet-700",
    bg: "bg-violet-50",
    border: "border-violet-200",
    badge: "bg-violet-100 text-violet-700",
    align: "center",
    meta: "Supervisor review",
  },
  {
    role: "L1 Support Agent",
    icon: User,
    text: "Your payment of ₹4,999 is in processing — typically settles in 4–6 hours. If it doesn't reflect by tonight, I'll initiate a manual refund. Would you like me to set a reminder?",
    color: "text-indigo-700",
    bg: "bg-indigo-50",
    border: "border-indigo-200",
    badge: "bg-indigo-100 text-indigo-700",
    align: "right",
    meta: null,
  },
  {
    role: "Customer",
    text: "It's been 12 hours already bro! Main bahut frustrated hoon. Supervisor se baat karo please!",
    icon: MessageSquare,
    color: "text-slate-700",
    bg: "bg-rose-50",
    border: "border-rose-200",
    badge: "bg-slate-200 text-slate-700",
    align: "left",
    meta: "😤 Frustration: 0.78 — Hinglish triggered",
  },
  {
    role: "L2 Supervisor",
    icon: Shield,
    text: "Escalating — 12h+ payment stuck, frustrated customer, high-priority. L3 Manager notified with full context.",
    color: "text-violet-700",
    bg: "bg-violet-50",
    border: "border-violet-200",
    badge: "bg-violet-100 text-violet-700",
    align: "center",
    meta: "Escalating to L3",
  },
  {
    role: "L3 Manager",
    icon: Crown,
    text: "VIP override applied. Initiating immediate refund of ₹4,999 + ₹200 goodwill credit. Payment will appear within 2 hours. I personally apologise for the delay.",
    color: "text-amber-700",
    bg: "bg-amber-50",
    border: "border-amber-200",
    badge: "bg-amber-100 text-amber-700",
    align: "right",
    meta: "Final authority",
  },
  {
    role: "Resolved",
    icon: CheckCircle,
    text: "Ticket closed. GRPO reward computed: empathy +0.82, policy adherence +0.91, resolution +1.0, SLA penalty -0.15 (escalation took 2 steps). Net reward: 0.74",
    color: "text-emerald-700",
    bg: "bg-emerald-50",
    border: "border-emerald-300",
    badge: "bg-emerald-100 text-emerald-700",
    align: "center",
    meta: "Reward signal",
  },
];

export function TestimonialMarquee() {
  return (
    <motion.section
      variants={staggerContainer}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="relative overflow-hidden bg-slate-50 py-24 md:py-32"
    >
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[700px] rounded-full bg-indigo-100/30 blur-[120px]" />
      </div>

      <div className="relative mx-auto max-w-3xl px-6">
        <motion.div variants={fadeUp} className="mb-12 text-center">
          <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-widest text-indigo-600">
            Live Agent Dialogue
          </span>
          <h2
            className="mt-2 text-3xl font-bold text-slate-900 md:text-4xl"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
          >
            Hierarchical escalation{" "}
            <span className="gradient-text italic">in action</span>
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-sm text-slate-500">
            A real multi-turn ticket — UPI payment stuck, customer switches to Hinglish, hierarchy escalates to manager.
          </p>
        </motion.div>

        <div className="flex flex-col gap-3">
          {CONVERSATION.map((msg, i) => {
            const isCenter = msg.align === "center";
            const isRight = msg.align === "right";

            if (isCenter) {
              return (
                <div key={i} className="flex flex-col items-center gap-1">
                  {i > 0 && <ArrowDown className="h-4 w-4 text-slate-300" />}
                  <motion.div
                    variants={fadeUp}
                    className={`flex w-full max-w-md items-center gap-2 rounded-2xl border ${msg.border} ${msg.bg} px-4 py-2.5`}
                  >
                    <msg.icon className={`h-4 w-4 shrink-0 ${msg.color}`} />
                    <span className={`text-xs font-bold ${msg.color}`}>{msg.role}</span>
                    <span className="mx-1 text-slate-300">·</span>
                    <p className={`text-xs ${msg.color} leading-relaxed`}>{msg.text}</p>
                  </motion.div>
                  {msg.meta && (
                    <span className="text-[10px] font-medium text-slate-400">{msg.meta}</span>
                  )}
                </div>
              );
            }

            return (
              <div key={i} className={`flex flex-col gap-1 ${isRight ? "items-end" : "items-start"}`}>
                {i > 0 && (
                  <ArrowDown className={`h-4 w-4 text-slate-300 ${isRight ? "self-end mr-4" : "self-start ml-4"}`} />
                )}
                <motion.div
                  variants={fadeUp}
                  className={`w-full max-w-[85%] rounded-2xl border ${msg.border} ${msg.bg} p-4 shadow-sm`}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold ${msg.badge}`}>
                      <msg.icon className="h-3 w-3" />
                      {msg.role}
                    </span>
                    {msg.meta && (
                      <span className="text-[10px] text-slate-400">{msg.meta}</span>
                    )}
                  </div>
                  <p className={`text-sm leading-relaxed ${msg.color}`}>{msg.text}</p>
                </motion.div>
              </div>
            );
          })}
        </div>
      </div>
    </motion.section>
  );
}
