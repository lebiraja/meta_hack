"use client";

import { cn } from "@/lib/utils";

interface Props { sentiment: string | number; trajectory: (string | number)[]; }

function sentimentToFrustration(s: string | number): number {
  if (typeof s === "number") return Math.max(0, Math.min(1, s));
  const map: Record<string, number> = { frustrated: 0.85, angry: 1.0, annoyed: 0.7, confused: 0.5, neutral: 0.3, satisfied: 0.1, happy: 0.0 };
  return map[s.toLowerCase()] ?? 0.4;
}

export function FrustrationMeter({ sentiment, trajectory }: Props) {
  const frust = sentimentToFrustration(sentiment as string | number);
  const color = frust >= 0.7 ? "bg-red-500" : frust >= 0.4 ? "bg-amber-500" : "bg-emerald-500";
  const label = frust >= 0.7 ? "Frustrated" : frust >= 0.4 ? "Moderate" : "Calm";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Customer Mood</span>
        <span className={cn("text-[10px] font-semibold", frust >= 0.7 ? "text-red-600" : frust >= 0.4 ? "text-amber-600" : "text-emerald-600")}>
          {label}
        </span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-500", color)} style={{ width: `${frust * 100}%` }} />
      </div>
      {trajectory.length > 1 && (
        <div className="flex gap-px items-end h-4">
          {trajectory.slice(-12).map((s, i) => {
            const h = Math.round(sentimentToFrustration(s) * 14);
            return <div key={i} className="flex-1 rounded-sm bg-gray-200" style={{ height: `${Math.max(2, h)}px` }} />;
          })}
        </div>
      )}
    </div>
  );
}
