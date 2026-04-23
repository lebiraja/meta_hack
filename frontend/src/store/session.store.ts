"use client";

import { create } from "zustand";
import { api } from "@/lib/api";
import type {
  Action,
  ActionLogEntry,
  Observation,
  Reward,
  TaskName,
} from "@/types";

interface SessionStore {
  sessionId: string | null;
  task: TaskName;
  observation: Observation | null;
  reward: Reward | null;
  actionLog: ActionLogEntry[];
  finalScore: number | null;
  isDone: boolean;
  isLoading: boolean;
  error: string | null;

  resetSession: (task: TaskName) => Promise<void>;
  submitStep: (action: Action) => Promise<void>;
  clearSession: () => void;
  dismissError: () => void;
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  sessionId: null,
  task: "easy",
  observation: null,
  reward: null,
  actionLog: [],
  finalScore: null,
  isDone: false,
  isLoading: false,
  error: null,

  resetSession: async (task) => {
    set({
      isLoading: true,
      error: null,
      isDone: false,
      finalScore: null,
      actionLog: [],
      reward: null,
      observation: null,
    });
    try {
      const res = await api.reset(task);
      set({
        sessionId: res.session_id,
        task,
        observation: res.observation,
        isLoading: false,
      });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  submitStep: async (action) => {
    const { sessionId } = get();
    if (!sessionId) return;
    set({ isLoading: true, error: null });
    try {
      const res = await api.step(sessionId, action);
      set({
        observation: res.observation,
        reward: res.reward,
        isDone: res.done,
        finalScore: res.final_score ?? null,
        // Replace entirely — backend returns full cumulative log
        actionLog: res.info.action_log,
        isLoading: false,
      });
    } catch (e) {
      const err = e as Error & { status?: number };
      if (err.status === 404) {
        set({
          error: "Session expired — start a new one",
          isLoading: false,
          sessionId: null,
          observation: null,
        });
      } else {
        set({ error: err.message, isLoading: false });
      }
    }
  },

  clearSession: () =>
    set({
      sessionId: null,
      observation: null,
      reward: null,
      actionLog: [],
      finalScore: null,
      isDone: false,
      error: null,
    }),

  dismissError: () => set({ error: null }),
}));
