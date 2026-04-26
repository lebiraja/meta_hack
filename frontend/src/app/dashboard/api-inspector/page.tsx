"use client";

import { useState } from "react";
import { useSessionStore } from "@/store/session.store";
import { JsonViewer } from "@/components/dashboard/JsonViewer";
import { api } from "@/lib/api";

export default function ApiInspectorPage() {
  const { observation, reward, sessionId } = useSessionStore();
  const [replayData, setReplayData] = useState<unknown>(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayError, setReplayError] = useState<string | null>(null);

  const fetchReplay = async () => {
    if (!sessionId) return;
    setReplayLoading(true);
    setReplayError(null);
    try {
      const data = await api.getReplay(sessionId);
      setReplayData(data);
    } catch (e) {
      setReplayError((e as Error).message);
    } finally {
      setReplayLoading(false);
    }
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h1 className="text-base font-semibold text-gray-900">
          API Inspector
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Raw JSON from the last backend response.
          {sessionId && (
            <span className="ml-1">
              Session:{" "}
              <span className="font-mono text-gray-500">
                {sessionId.slice(0, 8)}…
              </span>
            </span>
          )}
        </p>
      </div>

      <JsonViewer data={observation} title="Last Observation" maxHeight={500} />
      <JsonViewer data={reward} title="Last Reward" maxHeight={300} />

      {/* Replay fetcher */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">Replay (completed session)</span>
          <button
            onClick={fetchReplay}
            disabled={!sessionId || replayLoading}
            className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 rounded
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {replayLoading ? "Loading…" : "Fetch Replay"}
          </button>
        </div>
        {replayError && (
          <p className="text-xs text-red-600">{replayError}</p>
        )}
        {replayData !== null && (
          <JsonViewer data={replayData} title="Replay Data" maxHeight={500} />
        )}
      </div>
    </div>
  );
}
