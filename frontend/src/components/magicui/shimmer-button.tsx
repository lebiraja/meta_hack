"use client";
import { cn } from "@/lib/utils";
import React from "react";

export function ShimmerButton({
  children,
  className,
  shimmerColor = "#ffffff",
  background = "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  shimmerColor?: string;
  background?: string;
}) {
  return (
    <button
      {...props}
      className={cn(
        "relative inline-flex h-11 cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-xl px-6 text-sm font-semibold text-white transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-indigo-500/30 active:scale-95",
        className
      )}
      style={{ background }}
    >
      <span
        className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent"
        style={{
          backgroundSize: "200% 100%",
          animation: "shimmer 2.5s linear infinite",
        }}
      />
      <span className="relative flex items-center gap-2">{children}</span>
    </button>
  );
}
