"use client";

import { useSessionStore } from "@/store/session.store";
import { SupportAgentActions } from "./SupportAgentActions";
import { SupervisorActions } from "./SupervisorActions";
import { ManagerActions } from "./ManagerActions";

export function ActionPanel() {
  const { observation, isLoading, isDone } = useSessionStore();

  if (!observation || isDone) return null;

  const role = observation.active_role;

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      {role === "support_agent" && <SupportAgentActions isLoading={isLoading} />}
      {role === "supervisor" && <SupervisorActions isLoading={isLoading} />}
      {role === "manager" && <ManagerActions isLoading={isLoading} />}
    </div>
  );
}
