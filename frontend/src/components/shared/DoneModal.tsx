"use client";

import { useState } from "react";
import { useSessionStore } from "@/store/session.store";
import { api } from "@/lib/api";
import { formatScore } from "@/lib/utils";

export function DoneModal() {
  const { finalScore, sessionId, task, clearSession, resetSession, isLoading } =
    useSessionStore();
  const [agentName, setAgentName] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!sessionId || !agentName.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.submitLeaderboard(sessionId, agentName.trim());
      setSubmitted(true);
    } catch (e) {
      setSubmitError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const scoreColor =
    finalScore !== null
      ? finalScore >= 0.8
        ? "text-green-400"
        : finalScore >= 0.5
        ? "text-indigo-400"
        : "text-orange-400"
      : "text-neutral-400";

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-neutral-900 border border-neutral-700 rounded-lg w-full max-w-sm p-6 space-y-5">
        <div className="space-y-1">
          <p className="text-xs text-neutral-500 uppercase tracking-wider">Episode Complete</p>
          <div className="text-center py-3">
            <div className={`text-5xl font-mono font-bold ${scoreColor}`}>
              {finalScore !== null ? formatScore(finalScore) : "—"}
            </div>
            <p className="text-xs text-neutral-500 mt-1">Final Score · {task}</p>
          </div>
        </div>

        <div className="border-t border-neutral-800 pt-4 space-y-3">
          {!submitted ? (
            <>
              <p className="text-xs text-neutral-500">Submit to leaderboard (optional)</p>
              <input
                placeholder="Your agent name"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                maxLength={32}
                className="w-full bg-neutral-800 border border-neutral-700 rounded px-3 py-2 text-sm text-neutral-100
                           placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && agentName.trim()) handleSubmit();
                }}
              />
              {submitError && (
                <p className="text-xs text-red-400">{submitError}</p>
              )}
              <button
                disabled={!agentName.trim() || submitting}
                onClick={handleSubmit}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded
                           font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {submitting ? "Submitting…" : "Submit Score"}
              </button>
            </>
          ) : (
            <p className="text-sm text-green-400 text-center py-1">
              Score submitted to leaderboard!
            </p>
          )}
        </div>

        <div className="flex gap-2">
          <button
            disabled={isLoading}
            onClick={() => resetSession(task)}
            className="flex-1 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-sm rounded
                       font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isLoading ? "…" : "Play Again"}
          </button>
          <button
            onClick={clearSession}
            className="flex-1 py-2 bg-neutral-900 hover:bg-neutral-800 text-neutral-400 text-sm rounded
                       font-medium transition-colors border border-neutral-800"
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}
