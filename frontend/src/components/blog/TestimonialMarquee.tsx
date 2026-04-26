"use client";
import { Marquee } from "@/components/magicui/marquee";
import { motion } from "framer-motion";
import { MessageSquare } from "lucide-react";
import { fadeIn, viewportOnce } from "@/lib/motion";

const DIALOGUES = [
  { role: "Customer", text: "My order #4821 hasn't arrived in 3 weeks.", color: "text-slate-300" },
  { role: "L1 Agent", text: "I see your order. Carrier delay — issuing $10 credit now.", color: "text-indigo-300" },
  { role: "Customer", text: "The refund I got was only $20, I paid $180!", color: "text-slate-300" },
  { role: "L2 Supervisor", text: "Escalation approved. Overriding limit for this ticket.", color: "text-violet-300" },
  { role: "Customer", text: "I need this resolved before my event tomorrow.", color: "text-slate-300" },
  { role: "L1 Agent", text: "Flagging as high-priority SLA ticket, escalating immediately.", color: "text-indigo-300" },
  { role: "L3 Manager", text: "VIP override applied. Full refund + 20% future discount issued.", color: "text-amber-300" },
  { role: "Customer", text: "The product arrived damaged, three separate items.", color: "text-slate-300" },
  { role: "L1 Agent", text: "Photo evidence logged. Replacement order created — 2-day shipping.", color: "text-indigo-300" },
  { role: "L2 Supervisor", text: "Policy exception granted for bundle replacement.", color: "text-violet-300" },
  { role: "Customer", text: "I've been waiting 40 minutes on hold already.", color: "text-slate-300" },
  { role: "L1 Agent", text: "I sincerely apologize. Waiving the restocking fee for this case.", color: "text-indigo-300" },
];

function DialogCard({ role, text, color }: { role: string; text: string; color: string }) {
  return (
    <div className="glass flex w-64 shrink-0 flex-col gap-2 rounded-2xl p-4">
      <div className="flex items-center gap-2">
        <MessageSquare className={`h-3.5 w-3.5 ${color}`} />
        <span className={`text-xs font-bold ${color}`}>{role}</span>
      </div>
      <p className="text-xs leading-relaxed text-slate-400">&ldquo;{text}&rdquo;</p>
    </div>
  );
}

export function TestimonialMarquee() {
  const half = Math.ceil(DIALOGUES.length / 2);
  const row1 = DIALOGUES.slice(0, half);
  const row2 = DIALOGUES.slice(half);

  return (
    <motion.section
      variants={fadeIn}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="relative overflow-hidden bg-[#060c1a] py-16"
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-[#060c1a] to-transparent z-10" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[#060c1a] to-transparent z-10" />

      <div className="mb-2 text-center">
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-600">
          Agent Dialogues
        </span>
      </div>

      <div className="space-y-4">
        <Marquee duration={40}>
          {row1.map((d, i) => <DialogCard key={i} {...d} />)}
        </Marquee>
        <Marquee duration={35} reverse>
          {row2.map((d, i) => <DialogCard key={i} {...d} />)}
        </Marquee>
      </div>
    </motion.section>
  );
}
