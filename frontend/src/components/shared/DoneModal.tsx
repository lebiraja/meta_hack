"use client";

import { useState } from "react";
import { useSessionStore } from "@/store/session.store";
import { api } from "@/lib/api";
import { formatScore } from "@/lib/utils";

export function DoneModal() {
  const { finalScore, sessionId, task, clearSession, resetSession, isLoading } = useSessionStore();
  const [agentName, setAgentName] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!sessionId || !agentName.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try { await api.submitLeaderboard(sessionId, agentName.trim()); setSubmitted(true); }
    catch (e) { setSubmitError((e as Error).message); }
    finally { setSubmitting(false); }
  };

  const scoreColor = finalScore !== null
    ? finalScore >= 0.8 ? "text-emerald-600"
    : finalScore >= 0.5 ? "text-indigo-600"
    : "text-orange-600"
    : "text-gray-400";

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-sm p-6 space-y-5 shadow-2xl">
        <div className="space-y-1">
          <p className="text-xs text-gray-400 uppercase tracking-wider font-bold">Episode Complete</p>
          <div className="text-center py-3">
            <div className={`text-5xl font-mono font-bold ${scoreColor}`}>
              {finalScore !== null ? formatScore(finalScore) : "—"}
            </div>
            <p className="text-xs text-gray-400 mt-1">Final Score · {task}</p>
          </div>
        </div>

        <div className="border-t border-gray-100 pt-4 space-y-3">
          {!submitted ? (
            <>
              <p className="text-xs text-gray-500">Submit to leaderboard (optional)</p>
              <input
                placeholder="Your agent name"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                maxLength={32}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900
                           placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
                onKeyDown={(e) => { if (e.key === "Enter" && agentName.trim()) handleSubmit(); }}
              />
              {submitError && <p className="text-xs text-red-600">{submitError}</p>}
              <button
                disabled={!agentName.trim() || submitting}
                onClick={handleSubmit}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg
                           font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
              >
                {submitting ? "Submitting…" : "Submit Score"}
              </button>
            </>
          ) : (
            <p className="text-sm text-emerald-600 text-center py-1 font-medium">Score submitted to leaderboard!</p>
          )}
        </div>

        <div className="flex gap-2">
          <button
            disabled={isLoading}
            onClick={() => resetSession(task)}
            className="flex-1 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-lg
                       font-semibold transition-colors disabled:opacity-40"
          >
            {isLoading ? "…" : "Play Again"}
          </button>
          <button
            onClick={clearSession}
            className="flex-1 py-2 bg-white hover:bg-gray-50 text-gray-500 text-sm rounded-lg
                       font-medium transition-colors border border-gray-200"
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}
