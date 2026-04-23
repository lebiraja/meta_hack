"use client";

import { useState } from "react";

interface Props {
  policyContext: string;
}

export function PolicyContextPanel({ policyContext }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (!policyContext) return null;

  return (
    <div className="space-y-1">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center justify-between w-full text-[10px] text-neutral-500 uppercase tracking-wider hover:text-neutral-400 transition-colors"
      >
        <span>Policy Context</span>
        <span>{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <div className="text-[10px] text-neutral-400 bg-neutral-900 border border-neutral-800 rounded p-2 leading-relaxed whitespace-pre-wrap">
          {policyContext}
        </div>
      )}
    </div>
  );
}
