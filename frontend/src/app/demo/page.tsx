"use client";

import { useState, useEffect } from "react";
import { useSessionStore } from "@/store/session.store";
import { useAutoPlay } from "@/hooks/useAutoPlay";
import { useHumanCustomer } from "@/hooks/useHumanCustomer";

// Chat & layout
import { ChatWindow } from "@/components/chat/ChatWindow";

// Demo-mode specific
import { ModeToggle, type DemoMode } from "@/components/demo/ModeToggle";
import { AutoPlayControls } from "@/components/demo/AutoPlayControls";
import { CustomerChatInput } from "@/components/demo/CustomerChatInput";

// Sidebar panels
import { TicketInfoPanel } from "@/components/panels/TicketInfoPanel";
import { HierarchyPanel } from "@/components/panels/HierarchyPanel";
import { RetrievedDataPanel } from "@/components/panels/RetrievedDataPanel";
import { PolicyContextPanel } from "@/components/panels/PolicyContextPanel";
import { FrustrationMeter } from "@/components/indicators/FrustrationMeter";
import { ActiveRoleIndicator } from "@/components/indicators/ActiveRoleIndicator";

// Alerts
import { PolicyDriftAlert } from "@/components/alerts/PolicyDriftAlert";
import { SupervisorFeedbackBanner } from "@/components/alerts/SupervisorFeedbackBanner";
import { ManagerDirectiveBanner } from "@/components/alerts/ManagerDirectiveBanner";

// Charts & shared
import { RewardBreakdown } from "@/components/charts/RewardBreakdown";
import { TaskSelector } from "@/components/shared/TaskSelector";
import { DoneModal } from "@/components/shared/DoneModal";
import { ErrorToast } from "@/components/shared/ErrorToast";

export default function DemoPage() {
  const { observation, reward, isDone, isLoading, sessionId } = useSessionStore();
  const [mode, setMode] = useState<DemoMode>("auto");

  const autoPlay = useAutoPlay();
  const humanCustomer = useHumanCustomer();

  // Stop auto-play when switching modes
  const handleModeChange = (newMode: DemoMode) => {
    if (mode === "auto") autoPlay.stop();
    setMode(newMode);
  };

  // Stop auto-play when session is reset
  useEffect(() => {
    autoPlay.stop();
    humanCustomer.resetVirtualMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const isAutoThinking = autoPlay.isThinking;
  const showBanners =
    observation?.environment_event ||
    observation?.supervisor_feedback ||
    observation?.manager_directive;

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-neutral-950">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-800 flex-shrink-0 gap-3">
        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="text-sm font-semibold tracking-tight text-neutral-100">
            Agent<span className="text-indigo-400">OS</span>
          </span>
          {observation && (
            <span className="text-xs text-neutral-600 font-mono hidden lg:block">
              {observation.task} · {observation.ticket_id}
            </span>
          )}
        </div>

        {/* Mode toggle — centered */}
        <ModeToggle mode={mode} onChange={handleModeChange} />

        <div className="flex items-center gap-3 flex-shrink-0">
          <a
            href="/blog"
            className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors hidden sm:block"
          >
            ← Paper
          </a>
          <a
            href="/dashboard"
            className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors hidden sm:block"
          >
            Dashboard →
          </a>
          <TaskSelector />
        </div>
      </header>

      {/* ── Main layout ─────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left: chat area ──────────────────────────────────────── */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          {/* Banners (all modes) */}
          {showBanners && (
            <div className="flex-shrink-0 space-y-1 px-3 pt-2">
              {observation?.environment_event && (
                <PolicyDriftAlert event={observation.environment_event} />
              )}
              {observation?.supervisor_feedback && (
                <SupervisorFeedbackBanner feedback={observation.supervisor_feedback} />
              )}
              {observation?.manager_directive && (
                <ManagerDirectiveBanner directive={observation.manager_directive} />
              )}
            </div>
          )}

          {/* ── Chat area — switches based on mode ─────────────────── */}
          {mode === "customer" ? (
            /* Customer mode: custom chat UI with virtualMessages */
            <CustomerChatInput
              virtualMessages={humanCustomer.virtualMessages}
              isThinking={humanCustomer.isThinking}
              isDone={isDone}
              activeRole={observation?.active_role}
              error={humanCustomer.error}
              onSend={humanCustomer.sendCustomerMessage}
            />
          ) : (
            /* Auto-play and Manual modes: standard chat window */
            <>
              <div className="flex-1 overflow-y-auto px-3 py-3">
                {observation ? (
                  <ChatWindow messages={observation.conversation_history} />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full gap-3">
                    <div className="text-neutral-700 text-3xl select-none">◈</div>
                    <p className="text-sm text-neutral-600 text-center max-w-xs">
                      Select a task, click New Session, then press Play to watch the AI handle it.
                    </p>
                  </div>
                )}
              </div>

              {/* Progress bar */}
              {observation && (
                <div className="flex-shrink-0 px-3 pb-2 flex items-center gap-3">
                  <span className="text-[10px] text-neutral-600 font-mono flex-shrink-0">
                    {observation.step}/{observation.max_steps}
                  </span>
                  <div className="flex-1 h-0.5 bg-neutral-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(
                          100,
                          (observation.step / observation.max_steps) * 100
                        )}%`,
                      }}
                    />
                  </div>
                  {reward && (
                    <span className="text-[10px] font-mono text-indigo-400 flex-shrink-0">
                      {Math.round(reward.value * 100)}%
                    </span>
                  )}
                  {(isLoading || isAutoThinking) && (
                    <span className="text-[10px] text-neutral-600 animate-pulse flex-shrink-0">
                      …
                    </span>
                  )}
                </div>
              )}

              {/* Auto-play controls */}
              <AutoPlayControls
                autoPlay={autoPlay}
                activeRole={observation?.active_role}
                hasSession={!!observation && !isDone}
              />
            </>
          )}
        </div>

        {/* ── Right sidebar (all modes) ─────────────────────────────── */}
        <aside className="w-64 xl:w-72 flex-shrink-0 border-l border-neutral-800 overflow-y-auto p-3 space-y-4 hidden md:block">
          {observation ? (
            <>
              <TicketInfoPanel observation={observation} />

              <div className="border-t border-neutral-800 pt-3">
                <FrustrationMeter
                  sentiment={observation.customer_sentiment}
                  trajectory={observation.mood_trajectory}
                />
              </div>

              {observation.active_role && (
                <ActiveRoleIndicator
                  role={observation.active_role}
                  isLoading={isLoading || isAutoThinking}
                />
              )}

              {observation.hierarchy_state && (
                <div className="border-t border-neutral-800 pt-3">
                  <HierarchyPanel
                    state={observation.hierarchy_state}
                    activeRole={observation.active_role}
                  />
                </div>
              )}

              <div className="border-t border-neutral-800 pt-3">
                <RetrievedDataPanel observation={observation} />
              </div>

              {observation.unresolved_issues.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[10px] text-neutral-500 uppercase tracking-wider">
                    Unresolved
                  </span>
                  <div className="space-y-1">
                    {observation.unresolved_issues.map((issue) => (
                      <div
                        key={issue}
                        className="text-[10px] text-orange-400 bg-orange-500/10 border border-orange-500/20 rounded px-2 py-1"
                      >
                        {issue}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {observation.escalation_chain.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[10px] text-neutral-500 uppercase tracking-wider">
                    Escalation Chain
                  </span>
                  <div className="space-y-0.5">
                    {observation.escalation_chain.map((step, i) => (
                      <div
                        key={i}
                        className="text-[10px] text-neutral-500 font-mono bg-neutral-900 rounded px-2 py-0.5"
                      >
                        {i + 1}. {step}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {reward && (
                <div className="border-t border-neutral-800 pt-3">
                  <RewardBreakdown reward={reward} />
                </div>
              )}

              <div className="border-t border-neutral-800 pt-3">
                <PolicyContextPanel policyContext={observation.policy_context} />
              </div>
            </>
          ) : (
            <div className="text-xs text-neutral-700 text-center pt-8">
              No active session
            </div>
          )}
        </aside>
      </div>

      {isDone && <DoneModal />}
      <ErrorToast />
    </div>
  );
}
