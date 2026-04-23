"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "./ChatMessage";
import type { Message } from "@/types";

interface Props {
  messages: Message[];
}

export function ChatWindow({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm text-neutral-600">No messages yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 pb-2">
      {messages.map((msg, i) => (
        <ChatMessage key={i} message={msg} index={i} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
