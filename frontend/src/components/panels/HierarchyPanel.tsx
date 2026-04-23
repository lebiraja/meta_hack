import { cn } from "@/lib/utils";
import type { HierarchyState } from "@/types";

interface Props {
  state: HierarchyState;
  activeRole: string;
}

const PHASE_LABELS: Record<string, string> = {
  support_handling: "L1 Handling",
  supervisor_review: "L2 Review",
  manager_override: "L3 Override",
};

export function HierarchyPanel({ state, activeRole }: Props) {
  const counters = [
    {
      label: "L1 Actions",
      value: state.support_agent_actions,
      color: "text-indigo-400",
      active: activeRole === "support_agent",
    },
    {
      label: "L2 Reviews",
      value: state.supervisor_reviews,
      color: "text-amber-400",
      active: activeRole === "supervisor",
    },
    {
      label: "L3 Actions",
      value: state.manager_interventions,
      color: "text-rose-400",
      active: activeRole === "manager",
    },
  ];

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-neutral-500 uppercase tracking-wider">
          Hierarchy
        </span>
        <span className="text-[10px] font-mono text-neutral-400 bg-neutral-800 px-2 py-0.5 rounded">
          {PHASE_LABELS[state.current_phase] ?? state.current_phase}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-1.5">
        {counters.map(({ label, value, color, active }) => (
          <div
            key={label}
            className={cn(
              "text-center rounded p-2 border transition-colors",
              active
                ? "bg-neutral-800 border-neutral-700"
                : "bg-neutral-900 border-neutral-800"
            )}
          >
            <div className={cn("text-lg font-mono font-bold", color)}>
              {value}
            </div>
            <div className="text-[9px] text-neutral-600 leading-tight">
              {label}
            </div>
          </div>
        ))}
      </div>

      {state.escalation_reason && (
        <div className="text-[10px] text-amber-400/80 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1.5 leading-relaxed">
          <span className="font-medium">Escalation: </span>
          {state.escalation_reason}
        </div>
      )}

      {state.pending_l1_action && (
        <div className="text-[10px] text-neutral-400 bg-neutral-800 rounded px-2 py-1.5">
          <span className="text-neutral-500">Pending L1: </span>
          <span className="font-mono">
            {String(
              (state.pending_l1_action as Record<string, unknown>)
                .action_type ?? "—"
            )}
          </span>
        </div>
      )}
    </div>
  );
}
