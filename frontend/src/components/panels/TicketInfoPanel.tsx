import { PriorityBadge } from "@/components/badges/PriorityBadge";
import type { Observation } from "@/types";

interface Props {
  observation: Observation;
}

export function TicketInfoPanel({ observation }: Props) {
  return (
    <div className="space-y-2">
      <span className="text-[10px] text-neutral-500 uppercase tracking-wider">
        Ticket
      </span>
      <div className="space-y-1.5">
        <p className="text-sm font-medium text-neutral-100 leading-snug">
          {observation.subject}
        </p>
        <div className="flex items-center gap-2">
          <PriorityBadge priority={observation.priority} />
          <span className="text-[10px] text-neutral-500 uppercase">
            {observation.category}
          </span>
        </div>
        <p className="text-[10px] font-mono text-neutral-600">
          {observation.ticket_id}
        </p>
      </div>
    </div>
  );
}
