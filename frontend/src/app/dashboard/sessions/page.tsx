"use client";

import { useSessionStore } from "@/store/session.store";
import { StepTable } from "@/components/dashboard/StepTable";

export default function SessionsPage() {
  const { actionLog, sessionId, task } = useSessionStore();

  return (
    <div className="space-y-4 max-w-4xl">
      <div>
        <h1 className="text-base font-semibold text-gray-900">
          Session Logs
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          {sessionId
            ? `Session ${sessionId.slice(0, 8)}… · ${task}`
            : "No active session"}
        </p>
      </div>

      <StepTable entries={actionLog} />
    </div>
  );
}
