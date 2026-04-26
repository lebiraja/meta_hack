"use client";

import { useSessionStore } from "@/store/session.store";

export function ErrorToast() {
  const { error, dismissError } = useSessionStore();

  if (!error) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm">
      <div className="bg-white border border-red-200 rounded-xl px-4 py-3 shadow-lg flex items-start gap-3">
        <div className="flex-1">
          <p className="text-xs font-semibold text-red-600">Error</p>
          <p className="text-xs text-gray-600 mt-0.5">{error}</p>
        </div>
        <button
          onClick={dismissError}
          className="text-gray-400 hover:text-gray-600 text-sm leading-none flex-shrink-0"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
