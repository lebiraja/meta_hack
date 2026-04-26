import { PriorityBadge } from "@/components/badges/PriorityBadge";
import type { Observation } from "@/types";

interface Props { observation: Observation; }

export function TicketInfoPanel({ observation }: Props) {
  return (
    <div className="space-y-2">
      <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Ticket</span>
      <div className="space-y-1.5">
        <p className="text-sm font-semibold text-gray-900 leading-snug">{observation.subject}</p>
        <div className="flex items-center gap-2">
          <PriorityBadge priority={observation.priority} />
          <span className="text-[10px] text-gray-400 uppercase font-medium">{observation.category}</span>
        </div>
        <p className="text-[10px] font-mono text-gray-400">{observation.ticket_id}</p>
      </div>
    </div>
  );
}
