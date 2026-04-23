import { cn, roleDisplayName } from "@/lib/utils";
import { ROLE_TEXT_COLORS, ROLE_BORDER_COLORS } from "@/lib/constants";

interface Props {
  role: string;
  size?: "xs" | "sm";
}

export function RoleBadge({ role, size = "xs" }: Props) {
  const textColor = ROLE_TEXT_COLORS[role] ?? "text-neutral-400";
  const borderColor = ROLE_BORDER_COLORS[role] ?? "border-neutral-600";

  return (
    <span
      className={cn(
        "inline-flex items-center border rounded font-medium tracking-wide uppercase",
        size === "xs" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs",
        textColor,
        borderColor
      )}
    >
      {roleDisplayName(role)}
    </span>
  );
}
