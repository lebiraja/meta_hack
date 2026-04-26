"use client";

import { cn } from "@/lib/utils";
import { ROLE_TEXT_COLORS } from "@/lib/constants";
import { roleDisplayName } from "@/lib/utils";
import type { useAutoPlay } from "@/hooks/useAutoPlay";

type AutoPlayState = ReturnType<typeof useAutoPlay>;

interface Props {
  autoPlay: AutoPlayState;
  activeRole?: string;
  hasSession: boolean;
}

export function AutoPlayControls({ autoPlay, activeRole, hasSession }: Props) {
  const { isPlaying, isThinking, stepDelay, error, start, pause, stop, setStepDelay } = autoPlay;

  if (!hasSession) {
    return (
      <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
        <p className="text-xs text-gray-400 text-center">Start a session to begin auto-play</p>
      </div>
    );
  }

  const speedLabel = stepDelay <= 700 ? "Fast" : stepDelay <= 1500 ? "Normal" : "Slow";

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3 space-y-2.5">
      <div className="flex items-center gap-3">
        <button
          onClick={isPlaying ? pause : start}
          disabled={isThinking && !isPlaying}
          className={cn(
            "flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all",
            "disabled:opacity-40 disabled:cursor-not-allowed",
            isPlaying
              ? "bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200"
              : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm"
          )}
        >
          {isPlaying ? (
            <>
              <span className="w-2.5 h-2.5 border border-current rounded-sm flex-shrink-0" />
              Pause
            </>
          ) : (
            <>
              <span className="w-0 h-0 border-y-4 border-y-transparent border-l-[7px] border-l-current flex-shrink-0" />
              Play
            </>
          )}
        </button>

        {isThinking && (
          <div className="flex items-center gap-1.5">
            <span className="flex gap-0.5">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 120}ms` }}
                />
              ))}
            </span>
            <span className="text-xs text-gray-500">
              {activeRole ? `${roleDisplayName(activeRole)} is thinking…` : "AI thinking…"}
            </span>
          </div>
        )}

        {isPlaying && !isThinking && activeRole && (
          <div className="flex items-center gap-1.5">
            <span className={cn("w-1.5 h-1.5 rounded-full animate-pulse", ROLE_TEXT_COLORS[activeRole]?.replace("text-", "bg-") ?? "bg-indigo-500")} />
            <span className={cn("text-xs font-medium", ROLE_TEXT_COLORS[activeRole] ?? "text-indigo-600")}>{roleDisplayName(activeRole)}</span>
          </div>
        )}

        <div className="flex items-center gap-2 ml-auto">
          <span className="text-[10px] text-gray-400 w-10 text-right font-medium">{speedLabel}</span>
          <input
            type="range"
            min={500} max={3000} step={250}
            value={stepDelay}
            onChange={(e) => setStepDelay(Number(e.target.value))}
            className="w-20 h-1 appearance-none bg-gray-200 rounded-full cursor-pointer accent-indigo-600
                       [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3
                       [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-indigo-600
                       [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:cursor-pointer"
          />
        </div>
      </div>

      {error && (
        <div className="flex items-center justify-between text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          <span>{error}</span>
          <button onClick={stop} className="text-red-600 hover:text-red-800 ml-2 flex-shrink-0 font-medium">Dismiss</button>
        </div>
      )}
    </div>
  );
}
