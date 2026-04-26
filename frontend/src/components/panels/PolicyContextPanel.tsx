"use client";

import { useState } from "react";

interface Props { policyContext: string; }

export function PolicyContextPanel({ policyContext }: Props) {
  const [expanded, setExpanded] = useState(false);
  if (!policyContext) return null;

  return (
    <div className="space-y-1">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center justify-between w-full text-[10px] text-gray-400 uppercase tracking-wider font-semibold hover:text-gray-600 transition-colors"
      >
        <span>Policy Context</span>
        <span>{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <div className="text-[10px] text-gray-500 bg-gray-50 border border-gray-200 rounded-lg p-2 leading-relaxed whitespace-pre-wrap">
          {policyContext}
        </div>
      )}
    </div>
  );
}
