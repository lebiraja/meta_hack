"use client";

import { useRouter } from "next/navigation";
import { useSessionStore } from "@/store/session.store";
import { TASK_CONFIG, DIFFICULTY_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { TaskName } from "@/types";

interface Props {
  task: TaskName;
}

export function TaskCard({ task }: Props) {
  const config = TASK_CONFIG[task];
  const router = useRouter();
  const { resetSession, isLoading } = useSessionStore();

  const handleClick = async () => {
    await resetSession(task);
    router.push("/demo");
  };

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      className={cn(
        "w-full text-left p-3.5 rounded-lg border transition-all",
        "bg-neutral-900 border-neutral-800",
        "hover:bg-neutral-800 hover:border-neutral-700",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500",
        "disabled:opacity-50 disabled:cursor-not-allowed"
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-sm font-medium text-neutral-100 leading-tight">
          {config.label}
        </span>
        <span
          className={cn(
            "text-[9px] px-1.5 py-0.5 rounded border font-medium uppercase tracking-wide flex-shrink-0",
            DIFFICULTY_COLORS[config.difficulty]
          )}
        >
          {config.difficulty}
        </span>
      </div>
      <p className="text-[10px] text-neutral-500 mb-2 leading-relaxed">
        {config.description}
      </p>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px]">
        <div>
          <span className="text-neutral-600">Steps: </span>
          <span className="text-neutral-400">{config.maxSteps}</span>
        </div>
        <div>
          <span className="text-neutral-600">Levels: </span>
          <span className="text-neutral-400">
            L{config.levels.join("+L")}
          </span>
        </div>
        <div>
          <span className="text-neutral-600">Drift: </span>
          <span
            className={
              config.driftProbability > 0 ? "text-orange-400" : "text-neutral-600"
            }
          >
            {Math.round(config.driftProbability * 100)}%
          </span>
        </div>
        {config.hinglishEnabled && (
          <div className="text-yellow-400">Hinglish ✓</div>
        )}
      </div>
    </button>
  );
}
