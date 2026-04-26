"use client";
import { cn } from "@/lib/utils";

export function BorderBeam({
  size = 200,
  duration = 12,
  delay = 0,
  colorFrom = "#818cf8",
  colorTo = "#67e8f9",
  className,
}: {
  size?: number;
  duration?: number;
  delay?: number;
  colorFrom?: string;
  colorTo?: string;
  className?: string;
}) {
  return (
    <div
      className={cn("pointer-events-none absolute inset-0 rounded-[inherit]", className)}
      style={
        {
          "--size": size,
          "--duration": duration,
          "--delay": `-${delay}s`,
          "--color-from": colorFrom,
          "--color-to": colorTo,
        } as React.CSSProperties
      }
    >
      <div
        className="absolute inset-[1px] rounded-[inherit]"
        style={{
          background: `conic-gradient(from 0deg, transparent 0deg, ${colorFrom} 90deg, ${colorTo} 180deg, transparent 270deg)`,
          animation: `spin ${duration}s linear infinite`,
          animationDelay: `-${delay}s`,
        }}
      />
      <div className="absolute inset-[2px] rounded-[inherit] bg-slate-950" />
    </div>
  );
}

import React from "react";
