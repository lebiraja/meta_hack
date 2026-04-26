import { cn } from "@/lib/utils";
import type { HierarchyState } from "@/types";

interface Props { state: HierarchyState; activeRole: string; }

const PHASE_LABELS: Record<string, string> = {
  support_handling: "L1 Handling",
  supervisor_review: "L2 Review",
  manager_override: "L3 Override",
};

export function HierarchyPanel({ state, activeRole }: Props) {
  const counters = [
    { label: "L1 Actions", value: state.support_agent_actions, color: "text-indigo-600", active: activeRole === "support_agent" },
    { label: "L2 Reviews", value: state.supervisor_reviews, color: "text-amber-600", active: activeRole === "supervisor" },
    { label: "L3 Actions", value: state.manager_interventions, color: "text-rose-600", active: activeRole === "manager" },
  ];

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Hierarchy</span>
        <span className="text-[10px] font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md">
          {PHASE_LABELS[state.current_phase] ?? state.current_phase}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-1.5">
        {counters.map(({ label, value, color, active }) => (
          <div key={label} className={cn("text-center rounded-lg p-2 border transition-colors",
            active ? "bg-white border-gray-200 shadow-sm" : "bg-gray-50 border-gray-100")}>
            <div className={cn("text-lg font-mono font-bold", color)}>{value}</div>
            <div className="text-[9px] text-gray-400 leading-tight">{label}</div>
          </div>
        ))}
      </div>

      {state.escalation_reason && (
        <div className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1.5 leading-relaxed">
          <span className="font-semibold">Escalation: </span>{state.escalation_reason}
        </div>
      )}

      {state.pending_l1_action && (
        <div className="text-[10px] text-gray-500 bg-gray-50 border border-gray-100 rounded-lg px-2 py-1.5">
          <span className="text-gray-400">Pending L1: </span>
          <span className="font-mono">{String((state.pending_l1_action as Record<string, unknown>).action_type ?? "—")}</span>
        </div>
      )}
    </div>
  );
}
