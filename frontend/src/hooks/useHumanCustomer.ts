"use client";

import { useState, useCallback, useEffect } from "react";
import { useSessionStore } from "@/store/session.store";
import type { Message, Action } from "@/types";

interface UseHumanCustomerReturn {
  virtualMessages: Message[];
  isThinking: boolean;
  error: string | null;
  sendCustomerMessage: (text: string) => Promise<void>;
  resetVirtualMessages: () => void;
}

async function fetchAIAction(
  observation: import("@/types").Observation,
  virtualMessages: Message[]
): Promise<Action> {
  const res = await fetch("/api/ai-action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ observation, virtualMessages }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error((err as { error?: string }).error ?? `HTTP ${res.status}`);
  }
  const data = (await res.json()) as { action: Action; fallback?: boolean };
  return data.action;
}

/** Extract the display text from an agent action */
function getAgentMessageText(action: Action): string | null {
  return action.message ?? action.reason ?? action.feedback_to_agent ?? null;
}

/** Map action_type to the message role for display */
function getDisplayRole(actionType: string): Message["role"] {
  if (actionType.startsWith("supervisor")) return "supervisor";
  if (actionType.startsWith("manager")) return "manager";
  return "agent";
}

export function useHumanCustomer(): UseHumanCustomerReturn {
  const { observation, isDone, submitStep, sessionId } = useSessionStore();

  const [virtualMessages, setVirtualMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Seed the virtual conversation with the ticket's opening message on session start
  useEffect(() => {
    if (observation && virtualMessages.length === 0) {
      const firstCustomerMsg = observation.conversation_history.find(
        (m) => m.role === "customer"
      );
      if (firstCustomerMsg) {
        setVirtualMessages([firstCustomerMsg]);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const resetVirtualMessages = useCallback(() => {
    setVirtualMessages([]);
    setError(null);
  }, []);

  // Reset when session changes
  useEffect(() => {
    setVirtualMessages([]);
    setError(null);
  }, [sessionId]);

  const sendCustomerMessage = useCallback(
    async (text: string) => {
      const obs = useSessionStore.getState().observation;
      if (!obs || isDone || isThinking) return;

      setError(null);

      // 1. Append user's customer message to virtual conversation
      const customerMsg: Message = { role: "customer", content: text };
      const nextVirtual = [...virtualMessages, customerMsg];
      setVirtualMessages(nextVirtual);

      setIsThinking(true);

      try {
        // 2. Call AI with the virtual conversation as context
        const action = await fetchAIAction(obs, nextVirtual);

        // 3. Send action to backend for reward/state tracking
        await submitStep(action);

        // 4. Extract the agent's response text and show it
        const agentText = getAgentMessageText(action);
        const currentObs = useSessionStore.getState().observation;

        const agentRole = getDisplayRole(action.action_type);

        // Build the display message
        let displayContent = agentText ?? "";

        // For special terminal actions with no message, add a system note
        if (!agentText) {
          if (action.action_type === "close") {
            displayContent = "✓ Ticket closed as resolved.";
          } else if (action.action_type === "request_info") {
            displayContent =
              "I need some additional information to help you better. Could you please provide more details?";
          } else if (action.action_type === "supervisor_approve") {
            displayContent = "✓ Response approved.";
          }
        }

        const agentMsg: Message = {
          role: agentRole,
          content: displayContent,
        };

        setVirtualMessages([...nextVirtual, agentMsg]);

        // 5. If there's a system event (policy drift) from the new observation, add it
        if (currentObs?.environment_event && obs.environment_event !== currentObs.environment_event) {
          const systemMsg: Message = {
            role: "system",
            content: `[Policy Update] ${currentObs.environment_event}`,
          };
          setVirtualMessages((prev) => [...prev, systemMsg]);
        }
      } catch (e) {
        setError((e as Error).message);
        // Remove the customer message we optimistically added
        setVirtualMessages(virtualMessages);
      } finally {
        setIsThinking(false);
      }
    },
    [observation, isDone, isThinking, virtualMessages, submitStep]
  );

  return {
    virtualMessages,
    isThinking,
    error,
    sendCustomerMessage,
    resetVirtualMessages,
  };
}
