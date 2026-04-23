"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { LeaderboardEntry } from "@/types";

export function useLeaderboard(pollIntervalMs = 30000) {
  const [data, setData] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      try {
        const res = await api.getLeaderboard();
        if (!cancelled) {
          setData(res);
          setLoading(false);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError((e as Error).message);
          setLoading(false);
        }
      }
    };

    fetchData();
    const id = setInterval(fetchData, pollIntervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollIntervalMs]);

  return { data, loading, error };
}
