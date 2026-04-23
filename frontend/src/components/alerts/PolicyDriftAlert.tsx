"use client";

import { useRef, useState, useEffect } from "react";

interface Props {
  event: string;
}

export function PolicyDriftAlert({ event }: Props) {
  const prevEventRef = useRef<string | null>(null);
  const [isNew, setIsNew] = useState(false);

  useEffect(() => {
    if (event !== prevEventRef.current) {
      setIsNew(true);
      prevEventRef.current = event;
      const t = setTimeout(() => setIsNew(false), 3000);
      return () => clearTimeout(t);
    }
  }, [event]);

  return (
    <div
      className={`flex items-start gap-2 px-3 py-2 rounded border text-xs
        bg-amber-400/10 border-amber-400/30 text-amber-300
        ${isNew ? "ring-1 ring-amber-400/50" : ""}
        transition-all`}
    >
      <span className="flex-shrink-0 font-semibold text-amber-400 uppercase tracking-wide text-[10px] mt-0.5">
        Policy Drift
      </span>
      <span>{event}</span>
    </div>
  );
}
