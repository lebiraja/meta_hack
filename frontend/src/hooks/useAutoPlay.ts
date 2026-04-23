"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSessionStore } from "@/store/session.store";
import type { Action, Observation } from "@/types";

interface UseAutoPlayReturn {
  isPlaying: boolean;
  isThinking: boolean;
  stepDelay: number;
  error: string | null;
  start: () => void;
  pause: () => void;
  stop: () => void;
  setStepDelay: (ms: number) => void;
}

async function fetchAIAction(observation: Observation): Promise<Action> {
  const res = await fetch("/api/ai-action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ observation }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error((err as { error?: string }).error ?? `HTTP ${res.status}`);
  }
  const data = (await res.json()) as { action: Action; fallback?: boolean };
  return data.action;
}

export function useAutoPlay(): UseAutoPlayReturn {
  const { observation, isDone, isLoading, submitStep } = useSessionStore();

  const [isPlaying, setIsPlaying] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [stepDelay, setStepDelayState] = useState(1500);
  const [error, setError] = useState<string | null>(null);

  // Refs to avoid stale closures in the loop
  const isPlayingRef = useRef(false);
  const stepDelayRef = useRef(stepDelay);

  useEffect(() => {
    stepDelayRef.current = stepDelay;
  }, [stepDelay]);

  // Auto-stop when episode ends
  useEffect(() => {
    if (isDone && isPlayingRef.current) {
      isPlayingRef.current = false;
      setIsPlaying(false);
    }
  }, [isDone]);

  const runLoop = useCallback(async () => {
    while (isPlayingRef.current) {
      const obs = useSessionStore.getState().observation;
      const done = useSessionStore.getState().isDone;
      const loading = useSessionStore.getState().isLoading;

      if (!obs || done || !isPlayingRef.current) break;
      if (loading) {
        // Wait for previous step to complete
        await new Promise((r) => setTimeout(r, 200));
        continue;
      }

      setIsThinking(true);
      let action: Action;
      try {
        action = await fetchAIAction(obs);
      } catch (e) {
        setError((e as Error).message);
        isPlayingRef.current = false;
        setIsPlaying(false);
        setIsThinking(false);
        break;
      }
      setIsThinking(false);

      if (!isPlayingRef.current) break;

      await useSessionStore.getState().submitStep(action);

      // Check if done after step
      if (useSessionStore.getState().isDone) {
        isPlayingRef.current = false;
        setIsPlaying(false);
        break;
      }

      // Delay between steps so the user can watch
      await new Promise((r) => setTimeout(r, stepDelayRef.current));
    }
    setIsThinking(false);
  }, []);

  const start = useCallback(() => {
    if (!observation || isDone) return;
    setError(null);
    isPlayingRef.current = true;
    setIsPlaying(true);
    runLoop();
  }, [observation, isDone, runLoop]);

  const pause = useCallback(() => {
    isPlayingRef.current = false;
    setIsPlaying(false);
  }, []);

  const stop = useCallback(() => {
    isPlayingRef.current = false;
    setIsPlaying(false);
    setIsThinking(false);
    setError(null);
  }, []);

  const setStepDelay = useCallback((ms: number) => {
    setStepDelayState(ms);
    stepDelayRef.current = ms;
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      isPlayingRef.current = false;
    };
  }, []);

  // Stop playing if session is cleared
  useEffect(() => {
    if (!observation && isPlayingRef.current) {
      isPlayingRef.current = false;
      setIsPlaying(false);
    }
  }, [observation]);

  return {
    isPlaying,
    isThinking: isThinking || (isPlaying && isLoading),
    stepDelay,
    error,
    start,
    pause,
    stop,
    setStepDelay,
  };
}
