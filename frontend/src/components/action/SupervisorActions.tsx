"use client";

import { useState } from "react";
import { useSessionStore } from "@/store/session.store";
import type { Action } from "@/types";

interface Props {
  isLoading: boolean;
}

type Mode = "approve" | "reject" | "feedback" | "escalate" | null;

export function SupervisorActions({ isLoading }: Props) {
  const { submitStep } = useSessionStore();
  const [mode, setMode] = useState<Mode>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [reason, setReason] = useState("");

  const toggleMode = (m: Exclude<Mode, null>) => {
    setMode((prev) => (prev === m ? null : m));
    setFeedbackText("");
    setReason("");
  };

  const submit = async (action: Action) => {
    await submitStep(action);
    setMode(null);
    setFeedbackText("");
    setReason("");
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] text-amber-400 uppercase tracking-wider font-medium">Supervisor Review</span>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => submit({ action_type: "supervisor_approve", role: "supervisor" })}
          disabled={isLoading}
          className="px-3 py-1.5 bg-green-700/80 hover:bg-green-700 text-white text-xs rounded font-medium
                     transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Approve
        </button>
        <button
          onClick={() => toggleMode("feedback")}
          disabled={isLoading}
          className={`px-3 py-1.5 text-xs rounded font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
            ${mode === "feedback" ? "bg-amber-600 text-white" : "bg-amber-600/30 hover:bg-amber-600/50 text-amber-300"}`}
        >
          Give Feedback
        </button>
        <button
          onClick={() => toggleMode("reject")}
          disabled={isLoading}
          className={`px-3 py-1.5 text-xs rounded font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
            ${mode === "reject" ? "bg-red-700 text-white" : "bg-red-700/30 hover:bg-red-700/50 text-red-400"}`}
        >
          Reject
        </button>
        <button
          onClick={() => toggleMode("escalate")}
          disabled={isLoading}
          className={`px-3 py-1.5 text-xs rounded font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
            ${mode === "escalate" ? "bg-rose-700 text-white" : "bg-rose-700/30 hover:bg-rose-700/50 text-rose-400"}`}
        >
          Escalate to Manager
        </button>
      </div>

      {(mode === "feedback" || mode === "reject") && (
        <div className="flex gap-2">
          <textarea
            placeholder={
              mode === "reject"
                ? "Explain why this response is rejected…"
                : "Provide constructive feedback for the agent…"
            }
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            disabled={isLoading}
            rows={2}
            className="flex-1 bg-white border border-gray-200 rounded px-3 py-2 text-sm text-gray-900
                       placeholder:text-gray-400 focus:outline-none resize-none disabled:opacity-50
                       focus:ring-1 focus:ring-amber-500"
          />
          <button
            disabled={!feedbackText.trim() || isLoading}
            onClick={() =>
              submit({
                action_type: mode === "reject" ? "supervisor_reject" : "supervisor_feedback",
                feedback_to_agent: feedbackText,
                role: "supervisor",
              })
            }
            className={`self-end px-3 py-2 text-xs rounded font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
              ${mode === "reject"
                ? "bg-red-700 hover:bg-red-600 text-white"
                : "bg-amber-600 hover:bg-amber-500 text-white"}`}
          >
            {mode === "reject" ? "Reject" : "Send Feedback"}
          </button>
        </div>
      )}

      {mode === "escalate" && (
        <div className="flex gap-2">
          <input
            placeholder="Reason for escalating to manager…"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={isLoading}
            className="flex-1 bg-white border border-gray-200 rounded px-3 py-2 text-sm text-gray-900
                       placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-rose-500
                       disabled:opacity-50"
          />
          <button
            disabled={!reason.trim() || isLoading}
            onClick={() => submit({ action_type: "supervisor_escalate", reason, role: "supervisor" })}
            className="px-3 py-2 bg-rose-700 hover:bg-rose-600 text-white text-xs rounded font-medium
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Escalate
          </button>
        </div>
      )}
    </div>
  );
}
