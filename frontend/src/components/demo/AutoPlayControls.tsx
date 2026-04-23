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
      <div className="border-t border-neutral-800 px-4 py-3">
        <p className="text-xs text-neutral-600 text-center">
          Start a session to begin auto-play
        </p>
      </div>
    );
  }

  const speedLabel = stepDelay <= 700 ? "Fast" : stepDelay <= 1500 ? "Normal" : "Slow";

  return (
    <div className="border-t border-neutral-800 bg-neutral-950 px-4 py-3 space-y-2.5">
      {/* Controls row */}
      <div className="flex items-center gap-3">
        {/* Play / Pause button */}
        <button
          onClick={isPlaying ? pause : start}
          disabled={isThinking && !isPlaying}
          className={cn(
            "flex items-center gap-2 px-4 py-1.5 rounded text-xs font-medium transition-colors",
            "disabled:opacity-40 disabled:cursor-not-allowed",
            isPlaying
              ? "bg-neutral-700 hover:bg-neutral-600 text-neutral-200"
              : "bg-indigo-600 hover:bg-indigo-500 text-white"
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

        {/* Thinking indicator */}
        {isThinking && (
          <div className="flex items-center gap-1.5">
            <span className="flex gap-0.5">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 120}ms` }}
                />
              ))}
            </span>
            <span className="text-xs text-neutral-500">
              {activeRole ? `${roleDisplayName(activeRole)} is thinking…` : "AI thinking…"}
            </span>
          </div>
        )}

        {/* Active role badge when playing */}
        {isPlaying && !isThinking && activeRole && (
          <div className="flex items-center gap-1.5">
            <span
              className={cn(
                "w-1.5 h-1.5 rounded-full animate-pulse",
                ROLE_TEXT_COLORS[activeRole]?.replace("text-", "bg-") ?? "bg-indigo-400"
              )}
            />
            <span className={cn("text-xs", ROLE_TEXT_COLORS[activeRole] ?? "text-indigo-400")}>
              {roleDisplayName(activeRole)}
            </span>
          </div>
        )}

        {/* Speed control — far right */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-[10px] text-neutral-600 w-10 text-right">{speedLabel}</span>
          <input
            type="range"
            min={500}
            max={3000}
            step={250}
            value={stepDelay}
            onChange={(e) => setStepDelay(Number(e.target.value))}
            className="w-20 h-1 appearance-none bg-neutral-700 rounded-full cursor-pointer
                       [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3
                       [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-neutral-400
                       [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:cursor-pointer"
          />
          <span className="text-[10px] text-neutral-600 w-4">🐇</span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center justify-between text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded px-2 py-1.5">
          <span>{error}</span>
          <button
            onClick={stop}
            className="text-red-400 hover:text-red-300 ml-2 flex-shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
