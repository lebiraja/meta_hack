"use client";

import { useState, useRef, useEffect } from "react";
import { cn, detectHinglish, roleDisplayName } from "@/lib/utils";
import { ROLE_TEXT_COLORS } from "@/lib/constants";
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
        <span className="text-[10px] italic text-neutral-500 bg-neutral-900 border border-neutral-800 rounded px-2 py-1">
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
      <div
        className={cn(
          "flex items-center gap-1.5",
          isCustomer ? "flex-row-reverse" : "flex-row"
        )}
      >
        <span
          className={cn(
            "text-[9px] uppercase tracking-wide font-medium",
            isCustomer ? "text-indigo-400" : (ROLE_TEXT_COLORS[msg.role] ?? "text-neutral-400")
          )}
        >
          {isCustomer ? "You" : roleDisplayName(msg.role)}
        </span>
        {hasHinglish && (
          <span className="text-[9px] text-yellow-400 border border-yellow-400/30 bg-yellow-400/10 px-1 rounded">
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
            ? "bg-amber-500/15 border border-amber-500/20 text-amber-100 rounded-bl-sm"
            : msg.role === "manager"
            ? "bg-rose-500/15 border border-rose-500/20 text-rose-100 rounded-bl-sm"
            : "bg-neutral-800 text-neutral-100 rounded-bl-sm"
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
      <div className="bg-neutral-800 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-neutral-500 animate-bounce"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </div>
      {role && (
        <span
          className={cn(
            "text-[9px] uppercase tracking-wide pb-1",
            ROLE_TEXT_COLORS[role] ?? "text-neutral-500"
          )}
        >
          {roleDisplayName(role)} typing…
        </span>
      )}
    </div>
  );
}

export function CustomerChatInput({
  virtualMessages,
  isThinking,
  isDone,
  activeRole,
  error,
  onSend,
}: Props) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [virtualMessages.length, isThinking]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isThinking || sending || isDone) return;
    setInput("");
    setSending(true);
    try {
      await onSend(text);
    } finally {
      setSending(false);
      textareaRef.current?.focus();
    }
  };

  const isEmpty = virtualMessages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {isEmpty && !isDone ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-neutral-600 text-center max-w-xs">
              Start a session above, then type your first message as the customer.
            </p>
          </div>
        ) : (
          virtualMessages.map((msg, i) => <VirtualMessage key={i} msg={msg} />)
        )}
        {isThinking && <TypingIndicator role={activeRole} />}
        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mb-2 text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded px-2 py-1.5">
          {error}
        </div>
      )}

      {/* Done state */}
      {isDone ? (
        <div className="border-t border-neutral-800 px-4 py-3">
          <p className="text-xs text-neutral-500 text-center">
            Episode complete. Start a new session to continue.
          </p>
        </div>
      ) : (
        /* Input area */
        <div className="border-t border-neutral-800 px-4 py-3">
          <div className="flex gap-2">
            <textarea
              ref={textareaRef}
              placeholder="Type your message as the customer…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isThinking || sending || isEmpty}
              rows={2}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && input.trim()) {
                  handleSend();
                }
              }}
              className="flex-1 bg-neutral-900 border border-neutral-700 rounded-xl px-3 py-2 text-sm text-neutral-100
                         placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-indigo-500
                         resize-none disabled:opacity-50 transition-opacity"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isThinking || sending || isEmpty}
              className="self-end px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded-xl
                         font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {sending || isThinking ? "…" : "Send"}
            </button>
          </div>
          <p className="text-[10px] text-neutral-700 mt-1.5">
            ⌘↵ to send · AI responds as the support agent
          </p>
        </div>
      )}
    </div>
  );
}
