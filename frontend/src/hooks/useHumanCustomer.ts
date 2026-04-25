"use client";

import { useState, useCallback, useEffect } from "react";
import { useSessionStore } from "@/store/session.store";
import { api } from "@/lib/api";
import type { Message } from "@/types";

interface UseHumanCustomerReturn {
  virtualMessages: Message[];
  isThinking: boolean;
  error: string | null;
  sendCustomerMessage: (text: string) => Promise<void>;
  resetVirtualMessages: () => void;
}

function getDisplayRole(actionType: string): Message["role"] {
  if (actionType.startsWith("supervisor")) return "supervisor";
  if (actionType.startsWith("manager")) return "manager";
  return "agent";
}

export function useHumanCustomer(): UseHumanCustomerReturn {
  const { observation, isDone, sessionId } = useSessionStore();

  const [virtualMessages, setVirtualMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clear on session change — user will type their own opening message
  useEffect(() => {
    setVirtualMessages([]);
    setError(null);
  }, [sessionId]);

  const resetVirtualMessages = useCallback(() => {
    setVirtualMessages([]);
    setError(null);
  }, []);

  const sendCustomerMessage = useCallback(
    async (text: string) => {
      if (!sessionId || isDone || isThinking) return;

      setError(null);

      // Optimistically add the human's message
      const customerMsg: Message = { role: "customer", content: text };
      const nextVirtual = [...virtualMessages, customerMsg];
      setVirtualMessages(nextVirtual);
      setIsThinking(true);

      try {
        // Single round trip: env calls model internally and steps the environment
        const res = await api.chat(sessionId, text);

        // Sync done/finalScore into the session store
        useSessionStore.setState({
          isDone: res.done,
          finalScore: res.final_score ?? null,
        });

        const agentRole = getDisplayRole(res.action_type);
        let displayContent = res.agent_reply;
        if (!displayContent) {
          if (res.action_type === "close") {
            displayContent = "✓ Ticket closed as resolved.";
          } else if (res.action_type === "request_info") {
            displayContent =
              "I need some additional information to help you better. Could you please provide more details?";
          } else if (res.action_type === "supervisor_approve") {
            displayContent = "✓ Response approved.";
          }
        }

        const agentMsg: Message = { role: agentRole, content: displayContent };
        const withReply = [...nextVirtual, agentMsg];
        setVirtualMessages(withReply);

        if (res.environment_event) {
          setVirtualMessages((prev) => [
            ...prev,
            { role: "system", content: `[Policy Update] ${res.environment_event}` },
          ]);
        }
      } catch (e) {
        setError((e as Error).message);
        // Roll back the optimistic customer message
        setVirtualMessages(virtualMessages);
      } finally {
        setIsThinking(false);
      }
    },
    [sessionId, isDone, isThinking, virtualMessages]
  );

  return {
    virtualMessages,
    isThinking,
    error,
    sendCustomerMessage,
    resetVirtualMessages,
  };
}
