import { cn } from "@/lib/utils";
import { ROLE_TEXT_COLORS } from "@/lib/constants";
import { roleDisplayName } from "@/lib/utils";

interface Props { role: string; isLoading: boolean; }

export function ActiveRoleIndicator({ role, isLoading }: Props) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white border border-gray-200">
      <span className={cn("w-2 h-2 rounded-full flex-shrink-0", isLoading && "animate-pulse",
        ROLE_TEXT_COLORS[role]?.replace("text-", "bg-") ?? "bg-indigo-500")} />
      <span className="text-[10px] text-gray-400">Now acting:</span>
      <span className={cn("text-xs font-semibold", ROLE_TEXT_COLORS[role] ?? "text-indigo-600")}>
        {roleDisplayName(role)}
      </span>
    </div>
  );
}
