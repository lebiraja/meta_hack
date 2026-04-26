"use client";

import { useState } from "react";
import { useSessionStore } from "@/store/session.store";
import type { Action } from "@/types";

interface Props {
  isLoading: boolean;
}

type Mode =
  | "respond"
  | "request_info"
  | "escalate"
  | "close"
  | "query_user"
  | "query_order"
  | null;

export function SupportAgentActions({ isLoading }: Props) {
  const { submitStep } = useSessionStore();
  const [mode, setMode] = useState<Mode>(null);
  const [message, setMessage] = useState("");
  const [reason, setReason] = useState("");
  const [email, setEmail] = useState("");
  const [orderId, setOrderId] = useState("");

  const reset = () => {
    setMode(null);
    setMessage("");
    setReason("");
    setEmail("");
    setOrderId("");
  };

  const toggleMode = (m: Exclude<Mode, null>) => {
    setMode((prev) => (prev === m ? null : m));
    setMessage("");
    setReason("");
    setEmail("");
    setOrderId("");
  };

  const submit = async (action: Action) => {
    await submitStep(action);
    reset();
  };

  const actionButtons = [
    {
      id: "respond" as const,
      label: "Respond",
      color: "bg-indigo-600 hover:bg-indigo-500 text-white",
    },
    {
      id: "request_info" as const,
      label: "Request Info",
      color: "bg-neutral-700 hover:bg-neutral-600 text-gray-900",
    },
    {
      id: "query_user" as const,
      label: "Query User DB",
      color: "bg-cyan-700/80 hover:bg-cyan-600 text-white",
    },
    {
      id: "query_order" as const,
      label: "Query Order DB",
      color: "bg-teal-700/80 hover:bg-teal-600 text-white",
    },
    {
      id: "escalate" as const,
      label: "Escalate",
      color: "bg-orange-600/80 hover:bg-orange-600 text-white",
    },
    {
      id: "close" as const,
      label: "Close Ticket",
      color: "bg-green-700/80 hover:bg-green-700 text-white",
    },
  ];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {actionButtons.map(({ id, label, color }) => (
          <button
            key={id}
            onClick={() => toggleMode(id)}
            disabled={isLoading}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed
              ${mode === id ? "ring-1 ring-white/30 " + color : color}`}
          >
            {label}
          </button>
        ))}
      </div>

      {mode === "respond" && (
        <div className="flex gap-2">
          <textarea
            placeholder="Type your response to the customer…"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={isLoading}
            rows={3}
            className="flex-1 bg-white border border-gray-200 rounded px-3 py-2 text-sm text-gray-900
                       placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-500
                       resize-none disabled:opacity-50"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && message.trim()) {
                submit({ action_type: "respond", message, role: "support_agent" });
              }
            }}
          />
          <button
            disabled={!message.trim() || isLoading}
            onClick={() =>
              submit({ action_type: "respond", message, role: "support_agent" })
            }
            className="self-end px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded
                       font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      )}

      {mode === "escalate" && (
        <div className="flex gap-2">
          <input
            placeholder="Reason for escalation…"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={isLoading}
            className="flex-1 bg-white border border-gray-200 rounded px-3 py-2 text-sm text-gray-900
                       placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-orange-500
                       disabled:opacity-50"
          />
          <button
            disabled={!reason.trim() || isLoading}
            onClick={() =>
              submit({ action_type: "escalate", reason, role: "support_agent" })
            }
            className="px-3 py-2 bg-orange-600 hover:bg-orange-500 text-white text-xs rounded font-medium
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Escalate
          </button>
        </div>
      )}

      {mode === "request_info" && (
        <div className="flex gap-2">
          <input
            placeholder="What info do you need from the customer?"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={isLoading}
            className="flex-1 bg-white border border-gray-200 rounded px-3 py-2 text-sm text-gray-900
                       placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-500
                       disabled:opacity-50"
          />
          <button
            disabled={!message.trim() || isLoading}
            onClick={() =>
              submit({ action_type: "request_info", message, role: "support_agent" })
            }
            className="px-3 py-2 bg-neutral-700 hover:bg-neutral-600 text-gray-900 text-xs rounded
                       font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      )}

      {mode === "query_user" && (
        <div className="flex gap-2">
          <input
            placeholder="user@example.com — look up the account"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            className="flex-1 bg-white border border-cyan-700/50 rounded px-3 py-2 text-sm text-gray-900
                       placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-cyan-500
                       disabled:opacity-50 font-mono"
          />
          <button
            disabled={!email.trim() || isLoading}
            onClick={() =>
              submit({
                action_type: "query_user_profile",
                email: email.trim(),
                role: "support_agent",
              })
            }
            className="px-3 py-2 bg-cyan-700 hover:bg-cyan-600 text-white text-xs rounded font-medium
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Query
          </button>
        </div>
      )}

      {mode === "query_order" && (
        <div className="flex gap-2">
          <input
            placeholder="ORD-FD-8821 — look up the order"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            disabled={isLoading}
            className="flex-1 bg-white border border-teal-700/50 rounded px-3 py-2 text-sm text-gray-900
                       placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-teal-500
                       disabled:opacity-50 font-mono"
          />
          <button
            disabled={!orderId.trim() || isLoading}
            onClick={() =>
              submit({
                action_type: "query_order_details",
                order_id: orderId.trim(),
                role: "support_agent",
              })
            }
            className="px-3 py-2 bg-teal-700 hover:bg-teal-600 text-white text-xs rounded font-medium
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Query
          </button>
        </div>
      )}

      {mode === "close" && (
        <div className="flex items-center gap-3 p-2 bg-green-500/10 border border-green-500/20 rounded">
          <p className="text-xs text-green-300 flex-1">
            This will close the ticket as resolved. The episode will end.
          </p>
          <button
            disabled={isLoading}
            onClick={() =>
              submit({ action_type: "close", role: "support_agent" })
            }
            className="px-3 py-1.5 bg-green-700 hover:bg-green-600 text-white text-xs rounded font-medium
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
          >
            Confirm Close
          </button>
        </div>
      )}
    </div>
  );
}
