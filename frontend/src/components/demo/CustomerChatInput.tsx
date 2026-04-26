"use client";

import { useState, useRef, useEffect } from "react";
import { cn, detectHinglish, roleDisplayName } from "@/lib/utils";
import { ROLE_TEXT_COLORS } from "@/lib/constants";
import { useSessionStore } from "@/store/session.store";
import type { Message } from "@/types";

interface Props {
  virtualMessages: Message[];
  isThinking: boolean;
  isDone: boolean;
  activeRole?: string;
  error: string | null;
  onSend: (text: string) => Promise<void>;
}

function VirtualMessage({ msg }: { msg: Message }) {
  const isCustomer = msg.role === "customer";
  const isSystem = msg.role === "system";
  const hasHinglish = detectHinglish(msg.content);

  if (isSystem) {
    return (
      <div className="flex justify-center my-1">
        <span className="text-[10px] italic text-gray-400 bg-gray-50 border border-gray-200 rounded-full px-3 py-1">
          {msg.content}
        </span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-1 max-w-[80%]",
        isCustomer ? "items-end ml-auto" : "items-start mr-auto"
      )}
    >
      <div className={cn("flex items-center gap-1.5", isCustomer ? "flex-row-reverse" : "flex-row")}>
        <span
          className={cn(
            "text-[9px] uppercase tracking-wide font-semibold",
            isCustomer ? "text-indigo-600" : (ROLE_TEXT_COLORS[msg.role] ?? "text-gray-400")
          )}
        >
          {isCustomer ? "You" : roleDisplayName(msg.role)}
        </span>
        {hasHinglish && (
          <span className="text-[9px] text-amber-600 border border-amber-200 bg-amber-50 px-1.5 rounded-full font-medium">
            Hinglish
          </span>
        )}
      </div>
      <div
        className={cn(
          "rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
          isCustomer
            ? "bg-indigo-600 text-white rounded-br-sm"
            : msg.role === "supervisor"
            ? "bg-amber-50 border border-amber-200 text-amber-900 rounded-bl-sm"
            : msg.role === "manager"
            ? "bg-rose-50 border border-rose-200 text-rose-900 rounded-bl-sm"
            : "bg-gray-100 text-gray-800 rounded-bl-sm"
        )}
      >
        {msg.content}
      </div>
    </div>
  );
}

function TypingIndicator({ role }: { role?: string }) {
  return (
    <div className="flex items-end gap-2 max-w-[80%]">
      <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </div>
      {role && (
        <span className={cn("text-[9px] uppercase tracking-wide pb-1", ROLE_TEXT_COLORS[role] ?? "text-gray-400")}>
          {roleDisplayName(role)} typing…
        </span>
      )}
    </div>
  );
}

export function CustomerChatInput({ virtualMessages, isThinking, isDone, activeRole, error, onSend }: Props) {
  const { sessionId, observation } = useSessionStore();
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const hasSession = !!sessionId && !!observation;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [virtualMessages.length, isThinking]);

  useEffect(() => {
    if (hasSession && !isDone) textareaRef.current?.focus();
  }, [hasSession, isDone]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isThinking || sending || isDone || !hasSession) return;
    setInput("");
    setSending(true);
    try { await onSend(text); }
    finally { setSending(false); textareaRef.current?.focus(); }
  };

  const isEmpty = virtualMessages.length === 0;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {!hasSession ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-xs space-y-3">
              <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center mx-auto">
                <span className="text-xl">💬</span>
              </div>
              <p className="text-sm text-gray-500">
                Select a task and click <span className="text-gray-700 font-semibold">New Session</span> to start chatting as the customer.
              </p>
            </div>
          </div>
        ) : isEmpty && !isDone ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-sm space-y-3">
              <div className="w-12 h-12 bg-green-50 rounded-xl flex items-center justify-center mx-auto">
                <span className="text-xl">✍️</span>
              </div>
              <p className="text-sm text-gray-600 font-medium">Session ready! Type your issue below.</p>
              <p className="text-xs text-gray-400">
                Ticket: <span className="text-gray-500">{observation?.subject}</span>
              </p>
            </div>
          </div>
        ) : (
          virtualMessages.map((msg, i) => <VirtualMessage key={i} msg={msg} />)
        )}
        {isThinking && <TypingIndicator role={activeRole} />}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mx-4 mb-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {isDone ? (
        <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
          <p className="text-xs text-gray-400 text-center">Episode complete. Start a new session to continue.</p>
        </div>
      ) : (
        <div className="border-t border-gray-200 px-4 py-3 bg-white">
          <div className="flex gap-2">
            <textarea
              ref={textareaRef}
              placeholder={hasSession ? "Type your message as the customer…" : "Start a session first…"}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isThinking || sending || !hasSession}
              rows={2}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && input.trim()) handleSend();
              }}
              className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-900
                         placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300
                         resize-none disabled:opacity-50 transition-all"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isThinking || sending || !hasSession}
              className="self-end px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs rounded-xl
                         font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
            >
              {sending || isThinking ? "…" : "Send"}
            </button>
          </div>
          <p className="text-[10px] text-gray-400 mt-1.5">⌘↵ to send · AI responds as the support agent</p>
        </div>
      )}
    </div>
  );
}
