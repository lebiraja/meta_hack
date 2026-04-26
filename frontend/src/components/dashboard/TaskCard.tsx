"use client";

import { useRouter } from "next/navigation";
import { useSessionStore } from "@/store/session.store";
import { TASK_CONFIG, DIFFICULTY_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { TaskName } from "@/types";

interface Props { task: TaskName; }

export function TaskCard({ task }: Props) {
  const config = TASK_CONFIG[task];
  const router = useRouter();
  const { resetSession, isLoading } = useSessionStore();

  const handleClick = async () => { await resetSession(task); router.push("/demo"); };

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      className={cn(
        "w-full text-left p-3.5 rounded-xl border transition-all shadow-sm",
        "bg-white border-gray-200",
        "hover:bg-indigo-50/50 hover:border-indigo-200 hover:shadow-md",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/30",
        "disabled:opacity-50 disabled:cursor-not-allowed"
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-sm font-semibold text-gray-900 leading-tight">{config.label}</span>
        <span className={cn("text-[9px] px-1.5 py-0.5 rounded-md border font-bold uppercase tracking-wide flex-shrink-0", DIFFICULTY_COLORS[config.difficulty])}>
          {config.difficulty}
        </span>
      </div>
      <p className="text-[10px] text-gray-400 mb-2 leading-relaxed">{config.description}</p>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px]">
        <div><span className="text-gray-400">Steps: </span><span className="text-gray-600 font-medium">{config.maxSteps}</span></div>
        <div><span className="text-gray-400">Levels: </span><span className="text-gray-600 font-medium">L{config.levels.join("+L")}</span></div>
        <div><span className="text-gray-400">Drift: </span><span className={config.driftProbability > 0 ? "text-orange-600 font-medium" : "text-gray-400"}>{Math.round(config.driftProbability * 100)}%</span></div>
        {config.hinglishEnabled && <div className="text-amber-600 font-medium">Hinglish ✓</div>}
      </div>
    </button>
  );
}
