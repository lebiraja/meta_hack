"use client";
import { cn } from "@/lib/utils";
import React from "react";

export function Marquee({
  children,
  reverse = false,
  pauseOnHover = true,
  vertical = false,
  duration = 30,
  className,
}: {
  children: React.ReactNode;
  reverse?: boolean;
  pauseOnHover?: boolean;
  vertical?: boolean;
  duration?: number;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "group relative flex overflow-hidden",
        vertical ? "flex-col" : "flex-row",
        className
      )}
      style={{ "--duration": `${duration}s` } as React.CSSProperties}
    >
      {[0, 1].map((i) => (
        <div
          key={i}
          className={cn(
            "flex shrink-0 gap-4",
            vertical ? "flex-col" : "flex-row",
            reverse ? "animate-marquee-reverse" : "animate-marquee",
            pauseOnHover && "group-hover:[animation-play-state:paused]"
          )}
          style={{ "--duration": `${duration}s` } as React.CSSProperties}
          aria-hidden={i === 1}
        >
          {children}
        </div>
      ))}
    </div>
  );
}
