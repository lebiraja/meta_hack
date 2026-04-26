"use client";
import { TextReveal } from "@/components/magicui/text-reveal";
import { motion } from "framer-motion";
import { fadeIn, viewportOnce } from "@/lib/motion";

export function PullQuote({ text, attribution }: { text: string; attribution?: string }) {
  return (
    <section className="relative overflow-hidden bg-slate-50 py-20 md:py-28">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-transparent via-indigo-400 to-transparent" />
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-64 w-[600px] rounded-full bg-indigo-100/50 blur-[80px]" />
      </div>
      <div className="relative mx-auto max-w-4xl px-6 text-center">
        <TextReveal
          text={text}
          className="justify-center text-2xl font-semibold italic leading-relaxed text-slate-800 md:text-3xl lg:text-4xl"
        />
        {attribution && (
          <motion.p
            variants={fadeIn}
            initial="hidden"
            whileInView="visible"
            viewport={viewportOnce}
            className="mt-6 text-sm font-medium tracking-widest text-slate-400 uppercase"
          >
            — {attribution}
          </motion.p>
        )}
      </div>
    </section>
  );
}
