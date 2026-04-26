"use client";
import { cn } from "@/lib/utils";
import React from "react";

export function OrbitingCircle({
  children,
  radius = 80,
  duration = 20,
  delay = 0,
  reverse = false,
  className,
}: {
  children?: React.ReactNode;
  radius?: number;
  duration?: number;
  delay?: number;
  reverse?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "absolute flex items-center justify-center rounded-full",
        className
      )}
      style={
        {
          "--radius": `${radius}px`,
          "--orbit-duration": `${duration}s`,
          animation: `orbit ${duration}s linear ${delay}s infinite ${reverse ? "reverse" : "normal"}`,
          width: 40,
          height: 40,
          transformOrigin: "center",
        } as React.CSSProperties
      }
    >
      {children}
    </div>
  );
}
