"use client";
import { motion } from "framer-motion";
import { NumberTicker } from "@/components/magicui/number-ticker";
import { fadeIn } from "@/lib/motion";

const STATS = [
  { value: 17, prefix: "+", suffix: "pp", label: "Accuracy gain" },
  { value: 875, prefix: "", suffix: "×", label: "Token efficiency" },
  { value: 3, prefix: "", suffix: "", label: "Agent levels" },
  { value: 5, prefix: "", suffix: "", label: "Training stages" },
  { value: 12, prefix: "", suffix: "K+", label: "Training episodes" },
  { value: 94, prefix: "", suffix: "%", label: "Resolution rate" },
];

export function StatsBar() {
  return (
    <motion.div
      variants={fadeIn}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      className="sticky top-[65px] z-40 border-y border-white/8 bg-slate-950/90 backdrop-blur-xl"
    >
      <div className="mx-auto max-w-7xl overflow-x-auto">
        <div className="flex min-w-max items-center divide-x divide-white/8">
          {STATS.map(({ value, prefix, suffix, label }) => (
            <div key={label} className="flex flex-col items-center px-6 py-3 md:px-8">
              <span className="gradient-text text-xl font-bold tabular-nums md:text-2xl">
                <NumberTicker value={value} prefix={prefix} suffix={suffix} />
              </span>
              <span className="mt-0.5 text-[10px] font-medium uppercase tracking-widest text-slate-500">
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
