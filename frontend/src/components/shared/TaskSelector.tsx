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
        className="h-7 px-2 bg-white border border-gray-200 rounded-lg text-xs text-gray-700
                   focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 disabled:opacity-50
                   appearance-none cursor-pointer"
      >
        {(Object.keys(TASK_CONFIG) as TaskName[]).map((t) => (
          <option key={t} value={t}>{TASK_CONFIG[t].label}</option>
        ))}
      </select>
      <button
        disabled={isLoading}
        onClick={() => resetSession(selected)}
        className="h-7 px-3 bg-indigo-600 hover:bg-indigo-700 text-white text-xs rounded-lg font-semibold
                   transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
      >
        {isLoading ? "Starting…" : "New Session"}
      </button>
    </div>
  );
}
