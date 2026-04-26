"use client";

import { useState } from "react";
import { cn, truncate } from "@/lib/utils";
import { ROLE_TEXT_COLORS } from "@/lib/constants";
import type { ActionLogEntry } from "@/types";

interface Props { entries: ActionLogEntry[]; }
type SortKey = "step" | "role" | "action_type" | "reward";

export function StepTable({ entries }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("step");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sorted = [...entries].sort((a, b) => {
    const av = a[sortKey] ?? "";
    const bv = b[sortKey] ?? "";
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  };

  const ColHeader = ({ k, label, className = "" }: { k: SortKey; label: string; className?: string }) => (
    <th
      onClick={() => handleSort(k)}
      className={cn("text-left px-3 py-2 text-[10px] text-gray-400 uppercase tracking-wider font-bold",
        "cursor-pointer select-none hover:text-gray-600 transition-colors", className)}
    >
      {label}{sortKey === k ? <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span> : null}
    </th>
  );

  if (entries.length === 0) {
    return <div className="text-sm text-gray-400 text-center py-8 border border-gray-200 rounded-xl bg-white">No steps recorded yet.</div>;
  }

  return (
    <div className="overflow-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <ColHeader k="step" label="#" className="w-12" />
            <ColHeader k="role" label="Role" />
            <ColHeader k="action_type" label="Action" />
            <th className="text-left px-3 py-2 text-[10px] text-gray-400 uppercase tracking-wider font-bold">Message</th>
            <ColHeader k="reward" label="Reward" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((entry, i) => (
            <tr key={i} className="border-b border-gray-100 hover:bg-indigo-50/30 transition-colors">
              <td className="px-3 py-2 font-mono text-xs text-gray-400">{entry.step}</td>
              <td className={cn("px-3 py-2 text-xs font-medium", ROLE_TEXT_COLORS[entry.role ?? "agent"] ?? "text-gray-500")}>{entry.role ?? "agent"}</td>
              <td className="px-3 py-2 text-xs font-mono text-gray-600">{entry.action_type}</td>
              <td className="px-3 py-2 text-xs text-gray-500 max-w-xs">
                <span title={entry.message ?? entry.reason ?? entry.feedback ?? ""}>{truncate(entry.message ?? entry.reason ?? entry.feedback ?? "—", 60)}</span>
              </td>
              <td className={cn("px-3 py-2 text-xs font-mono font-medium",
                (entry.reward ?? 0) >= 0.7 ? "text-emerald-600" : (entry.reward ?? 0) >= 0.4 ? "text-amber-600" : "text-orange-600")}>
                {typeof entry.reward === "number" ? `${Math.round(entry.reward * 100)}%` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
