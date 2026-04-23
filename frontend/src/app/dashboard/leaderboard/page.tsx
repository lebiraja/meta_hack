"use client";

import { useState } from "react";
import { useLeaderboard } from "@/hooks/useLeaderboard";
import { useSessionStore } from "@/store/session.store";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function LeaderboardPage() {
  const { data, loading, error } = useLeaderboard(30000);
  const { sessionId, finalScore } = useSessionStore();

  const [showSubmit, setShowSubmit] = useState(false);
  const [agentName, setAgentName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!sessionId || !agentName.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await api.submitLeaderboard(sessionId, agentName.trim());
      setSubmitResult(res.message);
    } catch (e) {
      setSubmitError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-neutral-100">
            Leaderboard
          </h1>
          <p className="text-xs text-neutral-600 mt-0.5">
            Top agents by score. Refreshes every 30s.
          </p>
        </div>
        {finalScore !== null && sessionId && (
          <button
            onClick={() => setShowSubmit((v) => !v)}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded font-medium transition-colors"
          >
            Submit Score
          </button>
        )}
      </div>

      {/* Submit form */}
      {showSubmit && (
        <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-4 space-y-3">
          <p className="text-xs text-neutral-400">
            Submitting session{" "}
            <span className="font-mono">{sessionId?.slice(0, 8)}…</span> ·
            Score:{" "}
            <span className="text-indigo-400 font-mono">
              {finalScore !== null ? `${Math.round(finalScore * 100)}%` : "—"}
            </span>
          </p>
          <input
            placeholder="Agent name (3-32 chars)"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            maxLength={32}
            className="w-full bg-neutral-800 border border-neutral-700 rounded px-3 py-2 text-sm text-neutral-100
                       placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          {submitError && (
            <p className="text-xs text-red-400">{submitError}</p>
          )}
          {submitResult ? (
            <p className="text-xs text-green-400">{submitResult}</p>
          ) : (
            <button
              disabled={!agentName.trim() || submitting}
              onClick={handleSubmit}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded font-medium
                         transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {submitting ? "Submitting…" : "Submit"}
            </button>
          )}
        </div>
      )}

      {/* Table */}
      {loading && (
        <div className="text-xs text-neutral-600 py-4">Loading…</div>
      )}
      {error && (
        <div className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
          {error}
        </div>
      )}
      {!loading && !error && (
        <div className="overflow-auto rounded border border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-900 border-b border-neutral-800">
              <tr>
                {["Rank", "Agent", "Task", "Score", "Steps"].map((h) => (
                  <th
                    key={h}
                    className="text-left px-3 py-2 text-[10px] text-neutral-500 uppercase tracking-wider"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-3 py-6 text-center text-xs text-neutral-600"
                  >
                    No entries yet. Complete an episode to be the first!
                  </td>
                </tr>
              ) : (
                data.map((entry, i) => (
                  <tr
                    key={i}
                    className="border-b border-neutral-800/50 hover:bg-neutral-900/50 transition-colors"
                  >
                    <td className="px-3 py-2 text-xs text-neutral-500 font-mono">
                      {i + 1}
                    </td>
                    <td className="px-3 py-2 text-xs text-neutral-200 font-medium">
                      {entry.agent_name}
                    </td>
                    <td className="px-3 py-2 text-xs text-neutral-500 font-mono">
                      {entry.task_level}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 text-xs font-mono font-semibold",
                        entry.total_score >= 0.8
                          ? "text-green-400"
                          : entry.total_score >= 0.5
                          ? "text-indigo-400"
                          : "text-orange-400"
                      )}
                    >
                      {Math.round(entry.total_score * 100)}%
                    </td>
                    <td className="px-3 py-2 text-xs text-neutral-500 font-mono">
                      {entry.steps_taken}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
