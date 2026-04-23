"use client";

import { useSessionStore } from "@/store/session.store";
import { RewardBreakdown } from "@/components/charts/RewardBreakdown";
import { HierarchyPanel } from "@/components/panels/HierarchyPanel";
import { formatScore } from "@/lib/utils";

export default function OverviewPage() {
  const { sessionId, task, observation, reward, isDone, finalScore } =
    useSessionStore();

  const cards = [
    {
      label: "Session ID",
      value: sessionId ? sessionId.slice(0, 8) + "…" : "None",
      mono: true,
    },
    { label: "Task", value: task ?? "—", mono: false },
    {
      label: "Steps",
      value: observation
        ? `${observation.step} / ${observation.max_steps}`
        : "—",
      mono: true,
    },
    {
      label: "Latest Reward",
      value: reward ? formatScore(reward.value) : "—",
      mono: true,
      highlight: reward
        ? reward.value >= 0.7
          ? "text-green-400"
          : reward.value >= 0.4
          ? "text-yellow-400"
          : "text-orange-400"
        : undefined,
    },
  ];

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-base font-semibold text-neutral-100">Overview</h1>
        <p className="text-xs text-neutral-600 mt-0.5">
          Live session state from the active episode.
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {cards.map(({ label, value, mono, highlight }) => (
          <div
            key={label}
            className="bg-neutral-900 rounded-lg border border-neutral-800 p-3"
          >
            <div className="text-[10px] text-neutral-600 mb-1 uppercase tracking-wider">
              {label}
            </div>
            <div
              className={`text-sm truncate ${mono ? "font-mono" : "font-medium"} ${highlight ?? "text-neutral-200"}`}
            >
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Final score */}
      {isDone && finalScore !== null && (
        <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-4 text-center">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1">
            Final Score
          </div>
          <div className="text-4xl font-mono font-bold text-indigo-400">
            {formatScore(finalScore)}
          </div>
        </div>
      )}

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

      {!observation && !reward && (
        <div className="text-sm text-neutral-700 text-center py-12">
          No active session.{" "}
          <a href="/demo" className="text-indigo-500 hover:text-indigo-400">
            Start one →
          </a>
        </div>
      )}
    </div>
  );
}
