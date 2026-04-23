"use client";

import { useSessionStore } from "@/store/session.store";

export function ErrorToast() {
  const { error, dismissError } = useSessionStore();

  if (!error) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm">
      <div className="bg-neutral-900 border border-red-500/30 rounded-lg px-4 py-3 shadow-lg flex items-start gap-3">
        <div className="flex-1">
          <p className="text-xs font-medium text-red-400">Error</p>
          <p className="text-xs text-neutral-300 mt-0.5">{error}</p>
        </div>
        <button
          onClick={dismissError}
          className="text-neutral-600 hover:text-neutral-400 text-sm leading-none flex-shrink-0"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
