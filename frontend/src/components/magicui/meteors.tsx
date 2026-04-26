"use client";
import { cn } from "@/lib/utils";

export function Meteors({ number = 20, className }: { number?: number; className?: string }) {
  const meteors = Array.from({ length: number });
  return (
    <div className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      {meteors.map((_, i) => {
        const left = Math.floor(Math.random() * 100);
        const delay = Math.random() * 6;
        const duration = Math.random() * 4 + 3;
        const size = Math.floor(Math.random() * 2) + 1;
        return (
          <span
            key={i}
            className="absolute top-0 left-1/2 h-px rotate-[215deg] rounded-full bg-gradient-to-r from-transparent via-indigo-400 to-transparent opacity-0"
            style={{
              left: `${left}%`,
              width: `${80 + Math.random() * 120}px`,
              height: `${size}px`,
              animationName: "meteor",
              animationDuration: `${duration}s`,
              animationDelay: `${delay}s`,
              animationTimingFunction: "linear",
              animationIterationCount: "infinite",
              top: `-${Math.random() * 40}%`,
            }}
          />
        );
      })}
    </div>
  );
}
