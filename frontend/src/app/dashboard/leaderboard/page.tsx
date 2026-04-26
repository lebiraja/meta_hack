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
          <h1 className="text-base font-semibold text-gray-900">
            Leaderboard
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
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
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <p className="text-xs text-gray-500">
            Submitting session{" "}
            <span className="font-mono">{sessionId?.slice(0, 8)}…</span> ·
            Score:{" "}
            <span className="text-indigo-600 font-mono">
              {finalScore !== null ? `${Math.round(finalScore * 100)}%` : "—"}
            </span>
          </p>
          <input
            placeholder="Agent name (3-32 chars)"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            maxLength={32}
            className="w-full bg-gray-100 border border-gray-200 rounded px-3 py-2 text-sm text-gray-900
                       placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          {submitError && (
            <p className="text-xs text-red-600">{submitError}</p>
          )}
          {submitResult ? (
            <p className="text-xs text-emerald-600">{submitResult}</p>
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
        <div className="text-xs text-gray-400 py-4">Loading…</div>
      )}
      {error && (
        <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}
      {!loading && !error && (
        <div className="overflow-auto rounded border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-white border-b border-gray-200">
              <tr>
                {["Rank", "Agent", "Task", "Score", "Steps"].map((h) => (
                  <th
                    key={h}
                    className="text-left px-3 py-2 text-[10px] text-gray-400 uppercase tracking-wider"
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
                    className="px-3 py-6 text-center text-xs text-gray-400"
                  >
                    No entries yet. Complete an episode to be the first!
                  </td>
                </tr>
              ) : (
                data.map((entry, i) => (
                  <tr
                    key={i}
                    className="border-b border-gray-200/50 hover:bg-white/50 transition-colors"
                  >
                    <td className="px-3 py-2 text-xs text-gray-400 font-mono">
                      {i + 1}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-700 font-medium">
                      {entry.agent_name}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-400 font-mono">
                      {entry.task_level}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 text-xs font-mono font-semibold",
                        entry.total_score >= 0.8
                          ? "text-emerald-600"
                          : entry.total_score >= 0.5
                          ? "text-indigo-600"
                          : "text-orange-600"
                      )}
                    >
                      {Math.round(entry.total_score * 100)}%
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-400 font-mono">
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
