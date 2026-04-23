import { cn, roleDisplayName } from "@/lib/utils";
import { ROLE_TEXT_COLORS, ROLE_BG_COLORS } from "@/lib/constants";

interface Props {
  role: string;
  isLoading?: boolean;
}

export function ActiveRoleIndicator({ role, isLoading = false }: Props) {
  const textColor = ROLE_TEXT_COLORS[role] ?? "text-neutral-400";
  const bgColor = ROLE_BG_COLORS[role] ?? "bg-neutral-800";

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded border",
        bgColor,
        "border-neutral-800"
      )}
    >
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full flex-shrink-0",
          isLoading ? "bg-neutral-500" : textColor.replace("text-", "bg-"),
          !isLoading && "animate-pulse"
        )}
      />
      <span className="text-xs text-neutral-500">Now acting:</span>
      <span className={cn("text-xs font-medium", textColor)}>
        {roleDisplayName(role)}
      </span>
      {isLoading && (
        <span className="text-xs text-neutral-600 ml-auto">Processing…</span>
      )}
    </div>
  );
}
