import type {
  Action,
  TaskName,
  ResetResponse,
  StepResponse,
  LeaderboardEntry,
  ChatResponse,
} from "@/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7860";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ?? "meta_hack_2026";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : Array.isArray(body?.detail)
        ? body.detail.map((d: { msg?: string }) => d.msg).join(", ")
        : `HTTP ${res.status}`;
    const err = new Error(detail) as Error & { status: number };
    err.status = res.status;
    throw err;
  }

  return res.json() as Promise<T>;
}

export const api = {
  reset: (task: TaskName) =>
    apiFetch<ResetResponse>(`/reset?task=${task}`, { method: "POST" }),

  step: (sessionId: string, action: Action, humanCustomerMessage?: string) => {
    const params = new URLSearchParams({ session_id: sessionId });
    if (humanCustomerMessage) {
      params.set("human_customer_message", humanCustomerMessage);
    }
    return apiFetch<StepResponse>(`/step?${params.toString()}`, {
      method: "POST",
      body: JSON.stringify(action),
    });
  },

  getState: (sessionId: string) =>
    apiFetch<Record<string, unknown>>(`/state/${sessionId}`),

  getReplay: (sessionId: string) =>
    apiFetch<Record<string, unknown>>(`/replay/${sessionId}`),

  chat: (sessionId: string, message: string) =>
    apiFetch<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message }),
    }),

  getLeaderboard: () => apiFetch<LeaderboardEntry[]>("/leaderboard"),

  submitLeaderboard: (sessionId: string, agentName: string) =>
    apiFetch<{ status: string; message: string }>("/leaderboard/submit", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, agent_name: agentName }),
    }),
};
