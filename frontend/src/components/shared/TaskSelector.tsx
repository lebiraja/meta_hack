"use client";

import { useState } from "react";
import { useSessionStore } from "@/store/session.store";
import { TASK_CONFIG } from "@/lib/constants";
import type { TaskName } from "@/types";

export function TaskSelector() {
  const { resetSession, isLoading, task: currentTask } = useSessionStore();
  const [selected, setSelected] = useState<TaskName>(currentTask);

  return (
    <div className="flex items-center gap-2">
      <select
        value={selected}
        onChange={(e) => setSelected(e.target.value as TaskName)}
        disabled={isLoading}
        className="h-7 px-2 bg-neutral-900 border border-neutral-700 rounded text-xs text-neutral-200
                   focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50
                   appearance-none cursor-pointer"
      >
        {(Object.keys(TASK_CONFIG) as TaskName[]).map((t) => (
          <option key={t} value={t}>
            {TASK_CONFIG[t].label}
          </option>
        ))}
      </select>
      <button
        disabled={isLoading}
        onClick={() => resetSession(selected)}
        className="h-7 px-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded font-medium
                   transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? "Starting…" : "New Session"}
      </button>
    </div>
  );
}
