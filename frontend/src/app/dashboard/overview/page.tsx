"use client";

import { useSessionStore } from "@/store/session.store";
import { RewardBreakdown } from "@/components/charts/RewardBreakdown";
import { HierarchyPanel } from "@/components/panels/HierarchyPanel";
import { formatScore, roleDisplayName } from "@/lib/utils";
import { TASK_CONFIG, DIFFICULTY_COLORS } from "@/lib/constants";
import type { TaskName } from "@/types";

export default function OverviewPage() {
  const { sessionId, task, observation, reward, isDone, finalScore, actionLog } =
    useSessionStore();

  const taskConfig = TASK_CONFIG[task as TaskName];

  const cards = [
    {
      label: "Session",
      value: sessionId ? sessionId.slice(0, 12) + "…" : "No active session",
      mono: true,
      accent: sessionId ? "text-neutral-200" : "text-neutral-600",
    },
    {
      label: "Task",
      value: taskConfig?.label ?? task ?? "—",
      mono: false,
      accent: "text-neutral-200",
      badge: taskConfig ? { text: taskConfig.difficulty, color: DIFFICULTY_COLORS[taskConfig.difficulty] } : undefined,
    },
    {
      label: "Progress",
      value: observation
        ? `${observation.step} / ${observation.max_steps}`
        : "—",
      mono: true,
      accent: "text-neutral-200",
      progress: observation ? observation.step / observation.max_steps : 0,
    },
    {
      label: "Latest Reward",
      value: reward ? formatScore(reward.value) : "—",
      mono: true,
      accent: reward
        ? reward.value >= 0.7 ? "text-green-400"
        : reward.value >= 0.4 ? "text-yellow-400"
        : "text-orange-400"
        : "text-neutral-600",
    },
  ];

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-lg font-semibold text-neutral-100">Overview</h1>
          <p className="text-xs text-neutral-600 mt-0.5">
            Live session state from the active episode.
          </p>
        </div>
        {observation && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-neutral-600">Active Role:</span>
            <span className="text-xs font-medium text-indigo-400">
              {roleDisplayName(observation.active_role)}
            </span>
          </div>
        )}
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {cards.map(({ label, value, mono, accent, badge, progress }) => (
          <div
            key={label}
            className="bg-neutral-900 rounded-lg border border-neutral-800 p-4 space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-neutral-600 uppercase tracking-wider">
                {label}
              </span>
              {badge && (
                <span className={`text-[9px] px-1.5 py-0.5 rounded border font-medium uppercase ${badge.color}`}>
                  {badge.text}
                </span>
              )}
            </div>
            <div className={`text-base truncate ${mono ? "font-mono" : "font-medium"} ${accent}`}>
              {value}
            </div>
            {progress !== undefined && progress > 0 && (
              <div className="h-1 bg-neutral-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, progress * 100)}%` }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Final score banner */}
      {isDone && finalScore !== null && (
        <div className="bg-gradient-to-r from-indigo-500/10 via-indigo-500/5 to-transparent border border-indigo-500/20 rounded-lg p-6 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-neutral-500 uppercase tracking-wider">
              Episode Complete — Final Score
            </span>
            <p className="text-xs text-neutral-400 mt-1">
              Task: {taskConfig?.label ?? task} · Steps taken: {observation?.step ?? "?"}
            </p>
          </div>
          <div className="text-5xl font-mono font-bold text-indigo-400">
            {formatScore(finalScore)}
          </div>
        </div>
      )}

      {/* Two-column layout for reward + hierarchy */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Reward breakdown */}
        {reward && (
          <div className="bg-neutral-900 rounded-lg border border-neutral-800 p-4">
            <RewardBreakdown reward={reward} />
          </div>
        )}

        {/* Hierarchy state */}
        {observation?.hierarchy_state && (
          <div className="bg-neutral-900 rounded-lg border border-neutral-800 p-4">
            <HierarchyPanel
              state={observation.hierarchy_state}
              activeRole={observation.active_role}
            />
          </div>
        )}
      </div>

      {/* Task details card */}
      {taskConfig && observation && (
        <div className="bg-neutral-900 rounded-lg border border-neutral-800 p-4">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider mb-3">
            Task Configuration
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <span className="text-[10px] text-neutral-600 block">Max Steps</span>
              <span className="text-sm font-mono text-neutral-300">{taskConfig.maxSteps}</span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-600 block">Levels</span>
              <span className="text-sm font-mono text-neutral-300">L{taskConfig.levels.join("+L")}</span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-600 block">Policy Drift</span>
              <span className={`text-sm font-mono ${taskConfig.driftProbability > 0 ? "text-orange-400" : "text-neutral-600"}`}>
                {Math.round(taskConfig.driftProbability * 100)}%
              </span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-600 block">Features</span>
              <div className="flex gap-1.5 mt-0.5">
                {taskConfig.hierarchical && (
                  <span className="text-[9px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.5 rounded">Hierarchy</span>
                )}
                {taskConfig.hinglishEnabled && (
                  <span className="text-[9px] bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-1.5 py-0.5 rounded">Hinglish</span>
                )}
                {!taskConfig.hierarchical && !taskConfig.hinglishEnabled && (
                  <span className="text-[9px] text-neutral-600">Standard</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Unresolved issues */}
      {observation?.unresolved_issues &&
        observation.unresolved_issues.length > 0 && (
          <div className="bg-neutral-900 rounded-lg border border-neutral-800 p-4">
            <div className="text-[10px] text-neutral-500 uppercase tracking-wider mb-2">
              Unresolved Issues
            </div>
            <ul className="space-y-1">
              {observation.unresolved_issues.map((issue) => (
                <li key={issue} className="text-xs text-orange-400 flex items-center gap-1.5">
                  <span className="w-1 h-1 rounded-full bg-orange-400 flex-shrink-0" />
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

      {/* Recent actions mini-table */}
      {actionLog.length > 0 && (
        <div className="bg-neutral-900 rounded-lg border border-neutral-800 p-4">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider mb-3">
            Recent Actions
          </div>
          <div className="space-y-1.5">
            {actionLog.slice(-5).map((entry, i) => (
              <div key={i} className="flex items-center gap-3 text-xs">
                <span className="text-neutral-600 font-mono w-6">#{entry.step}</span>
                <span className="text-indigo-400 w-20 truncate">{entry.role ?? "agent"}</span>
                <span className="text-neutral-400 font-mono flex-1 truncate">{entry.action_type}</span>
                <span className={`font-mono ${
                  (entry.reward ?? 0) >= 0.7 ? "text-green-400" :
                  (entry.reward ?? 0) >= 0.4 ? "text-yellow-400" : "text-orange-400"
                }`}>
                  {typeof entry.reward === "number" ? `${Math.round(entry.reward * 100)}%` : "—"}
                </span>
              </div>
            ))}
          </div>
          {actionLog.length > 5 && (
            <a href="/dashboard/sessions" className="text-[10px] text-indigo-500 hover:text-indigo-400 mt-2 block">
              View all {actionLog.length} actions →
            </a>
          )}
        </div>
      )}

      {/* Empty state */}
      {!observation && !reward && (
        <div className="text-center py-16 space-y-3">
          <div className="text-neutral-700 text-4xl select-none">◈</div>
          <p className="text-sm text-neutral-600">
            No active session.
          </p>
          <a
            href="/demo"
            className="inline-block px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded-lg font-medium transition-colors"
          >
            Start a Demo →
          </a>
        </div>
      )}
    </div>
  );
}
