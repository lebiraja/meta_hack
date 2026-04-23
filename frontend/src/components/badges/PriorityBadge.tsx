import { cn } from "@/lib/utils";
import { PRIORITY_COLORS } from "@/lib/constants";
import type { Priority } from "@/types";

interface Props {
  priority: Priority;
}

export function PriorityBadge({ priority }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center border rounded px-1.5 py-0.5 text-[10px] font-medium tracking-wide uppercase",
        PRIORITY_COLORS[priority]
      )}
    >
      {priority}
    </span>
  );
}
