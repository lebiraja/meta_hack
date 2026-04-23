"use client";

import { useState } from "react";
import { useSessionStore } from "@/store/session.store";
import type { Action } from "@/types";

interface Props {
  isLoading: boolean;
}

type Mode = "override" | "resolve" | "send_back" | null;

export function ManagerActions({ isLoading }: Props) {
  const { submitStep } = useSessionStore();
  const [mode, setMode] = useState<Mode>(null);
  const [message, setMessage] = useState("");
  const [directive, setDirective] = useState("");

  const toggleMode = (m: Exclude<Mode, null>) => {
    setMode((prev) => (prev === m ? null : m));
    setMessage("");
    setDirective("");
  };

  const submit = async (action: Action) => {
    await submitStep(action);
    setMode(null);
    setMessage("");
    setDirective("");
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] text-rose-400 uppercase tracking-wider font-medium">Manager Override</span>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => toggleMode("override")}
          disabled={isLoading}
          className={`px-3 py-1.5 text-xs rounded font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
            ${mode === "override" ? "bg-rose-700 text-white" : "bg-rose-700/30 hover:bg-rose-700/50 text-rose-300"}`}
        >
          Direct Response
        </button>
        <button
          onClick={() => toggleMode("resolve")}
          disabled={isLoading}
          className={`px-3 py-1.5 text-xs rounded font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
            ${mode === "resolve" ? "bg-green-700 text-white" : "bg-green-700/30 hover:bg-green-700/50 text-green-400"}`}
        >
          Resolve &amp; Close
        </button>
        <button
          onClick={() => toggleMode("send_back")}
          disabled={isLoading}
          className={`px-3 py-1.5 text-xs rounded font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
            ${mode === "send_back" ? "bg-amber-700 text-white" : "bg-amber-700/30 hover:bg-amber-700/50 text-amber-400"}`}
        >
          Send Back to L1
        </button>
      </div>

      {(mode === "override" || mode === "resolve") && (
        <div className="flex gap-2">
          <textarea
            placeholder={
              mode === "resolve"
                ? "Final resolution message for the customer…"
                : "Manager response to send to the customer…"
            }
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={isLoading}
            rows={3}
            className="flex-1 bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm text-neutral-100
                       placeholder:text-neutral-600 focus:outline-none resize-none disabled:opacity-50
                       focus:ring-1 focus:ring-rose-500"
          />
          <button
            disabled={!message.trim() || isLoading}
            onClick={() =>
              submit({
                action_type: mode === "resolve" ? "manager_resolve" : "manager_override",
                message,
                role: "manager",
              })
            }
            className={`self-end px-3 py-2 text-xs rounded font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
              ${mode === "resolve"
                ? "bg-green-700 hover:bg-green-600 text-white"
                : "bg-rose-700 hover:bg-rose-600 text-white"}`}
          >
            {mode === "resolve" ? "Resolve" : "Send"}
          </button>
        </div>
      )}

      {mode === "send_back" && (
        <div className="flex gap-2">
          <textarea
            placeholder="Directive to the support agent…"
            value={directive}
            onChange={(e) => setDirective(e.target.value)}
            disabled={isLoading}
            rows={2}
            className="flex-1 bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm text-neutral-100
                       placeholder:text-neutral-600 focus:outline-none resize-none disabled:opacity-50
                       focus:ring-1 focus:ring-amber-500"
          />
          <button
            disabled={!directive.trim() || isLoading}
            onClick={() =>
              submit({ action_type: "manager_send_back", feedback_to_agent: directive, role: "manager" })
            }
            className="self-end px-3 py-2 bg-amber-700 hover:bg-amber-600 text-white text-xs rounded font-medium
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Send Back
          </button>
        </div>
      )}
    </div>
  );
}
