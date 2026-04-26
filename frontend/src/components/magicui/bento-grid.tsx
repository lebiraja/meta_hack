"use client";
import { cn } from "@/lib/utils";
import React from "react";

export function BentoGrid({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3",
        className
      )}
    >
      {children}
    </div>
  );
}

export function BentoCard({
  children,
  className,
  colSpan = 1,
  rowSpan = 1,
}: {
  children: React.ReactNode;
  className?: string;
  colSpan?: 1 | 2 | 3;
  rowSpan?: 1 | 2;
}) {
  const colClass = { 1: "", 2: "md:col-span-2", 3: "md:col-span-3" }[colSpan];
  const rowClass = { 1: "", 2: "md:row-span-2" }[rowSpan];
  return (
    <div
      className={cn(
        "glass group relative overflow-hidden rounded-2xl p-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/10",
        colClass,
        rowClass,
        className
      )}
    >
      {children}
    </div>
  );
}
