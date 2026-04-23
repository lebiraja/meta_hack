import { cn, detectHinglish } from "@/lib/utils";
import {
  ROLE_BG_COLORS,
  ROLE_TEXT_COLORS,
  ROLE_BORDER_COLORS,
} from "@/lib/constants";
import { RoleBadge } from "@/components/badges/RoleBadge";
import type { Message } from "@/types";

interface Props {
  message: Message;
  index?: number;
}

export function ChatMessage({ message, index }: Props) {
  const isSystem = message.role === "system";
  const hasHinglish = detectHinglish(message.content);

  const bgColor = ROLE_BG_COLORS[message.role] ?? "bg-neutral-900";
  const borderColor = ROLE_BORDER_COLORS[message.role] ?? "border-neutral-800";
  const textColor = ROLE_TEXT_COLORS[message.role] ?? "text-neutral-300";

  return (
    <div
      className={cn(
        "rounded px-3 py-2.5 space-y-1.5 border",
        bgColor,
        borderColor,
        isSystem && "border-dashed"
      )}
    >
      <div className="flex items-center gap-2">
        <RoleBadge role={message.role} />
        {hasHinglish && (
          <span className="text-[9px] font-medium text-yellow-400 border border-yellow-400/30 bg-yellow-400/10 px-1.5 py-0.5 rounded uppercase tracking-wide">
            Hinglish
          </span>
        )}
        {index !== undefined && (
          <span className="text-[10px] text-neutral-700 ml-auto font-mono">
            #{index}
          </span>
        )}
      </div>
      <p
        className={cn(
          "text-sm leading-relaxed whitespace-pre-wrap break-words",
          isSystem ? "italic text-neutral-500 text-xs" : textColor
        )}
      >
        {message.content}
      </p>
    </div>
  );
}
