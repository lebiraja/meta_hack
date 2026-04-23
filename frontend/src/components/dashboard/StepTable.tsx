"use client";

import { useState } from "react";
import { cn, truncate } from "@/lib/utils";
import { ROLE_TEXT_COLORS } from "@/lib/constants";
import type { ActionLogEntry } from "@/types";

interface Props {
  entries: ActionLogEntry[];
}

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
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const ColHeader = ({
    k,
    label,
    className = "",
  }: {
    k: SortKey;
    label: string;
    className?: string;
  }) => (
    <th
      onClick={() => handleSort(k)}
      className={cn(
        "text-left px-3 py-2 text-[10px] text-neutral-500 uppercase tracking-wider",
        "cursor-pointer select-none hover:text-neutral-300 transition-colors",
        className
      )}
    >
      {label}
      {sortKey === k ? (
        <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>
      ) : null}
    </th>
  );

  if (entries.length === 0) {
    return (
      <div className="text-sm text-neutral-600 text-center py-8 border border-neutral-800 rounded">
        No steps recorded yet.
      </div>
    );
  }

  return (
    <div className="overflow-auto rounded border border-neutral-800">
      <table className="w-full text-sm">
        <thead className="bg-neutral-900 border-b border-neutral-800">
          <tr>
            <ColHeader k="step" label="#" className="w-12" />
            <ColHeader k="role" label="Role" />
            <ColHeader k="action_type" label="Action" />
            <th className="text-left px-3 py-2 text-[10px] text-neutral-500 uppercase tracking-wider">
              Message
            </th>
            <ColHeader k="reward" label="Reward" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((entry, i) => (
            <tr
              key={i}
              className="border-b border-neutral-800/50 hover:bg-neutral-900/50 transition-colors"
            >
              <td className="px-3 py-2 font-mono text-xs text-neutral-500">
                {entry.step}
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-xs",
                  ROLE_TEXT_COLORS[entry.role ?? "agent"] ?? "text-neutral-400"
                )}
              >
                {entry.role ?? "agent"}
              </td>
              <td className="px-3 py-2 text-xs font-mono text-neutral-300">
                {entry.action_type}
              </td>
              <td className="px-3 py-2 text-xs text-neutral-500 max-w-xs">
                <span title={entry.message ?? entry.reason ?? entry.feedback ?? ""}>
                  {truncate(
                    entry.message ?? entry.reason ?? entry.feedback ?? "—",
                    60
                  )}
                </span>
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-xs font-mono",
                  (entry.reward ?? 0) >= 0.7
                    ? "text-green-400"
                    : (entry.reward ?? 0) >= 0.4
                    ? "text-yellow-400"
                    : "text-orange-400"
                )}
              >
                {typeof entry.reward === "number"
                  ? `${Math.round(entry.reward * 100)}%`
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
