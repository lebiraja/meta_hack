import { cn, roleDisplayName } from "@/lib/utils";
import { ROLE_TEXT_COLORS, ROLE_BORDER_COLORS } from "@/lib/constants";

interface Props { role: string; size?: "xs" | "sm"; }

export function RoleBadge({ role, size = "xs" }: Props) {
  const textColor = ROLE_TEXT_COLORS[role] ?? "text-gray-500";
  const borderColor = ROLE_BORDER_COLORS[role] ?? "border-gray-200";

  return (
    <span className={cn(
      "inline-flex items-center border rounded-md font-semibold tracking-wide uppercase",
      size === "xs" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs",
      textColor, borderColor
    )}>
      {roleDisplayName(role)}
    </span>
  );
}
