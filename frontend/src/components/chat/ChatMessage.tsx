import { cn, detectHinglish } from "@/lib/utils";
import { ROLE_BG_COLORS, ROLE_TEXT_COLORS, ROLE_BORDER_COLORS } from "@/lib/constants";
import { RoleBadge } from "@/components/badges/RoleBadge";
import type { Message } from "@/types";

interface Props {
  message: Message;
  index?: number;
}

export function ChatMessage({ message, index }: Props) {
  const isSystem = message.role === "system";
  const hasHinglish = detectHinglish(message.content);

  const bgColor = ROLE_BG_COLORS[message.role] ?? "bg-gray-50";
  const borderColor = ROLE_BORDER_COLORS[message.role] ?? "border-gray-200";
  const textColor = ROLE_TEXT_COLORS[message.role] ?? "text-gray-600";

  return (
    <div
      className={cn(
        "rounded-lg px-3 py-2.5 space-y-1.5 border",
        bgColor, borderColor,
        isSystem && "border-dashed"
      )}
    >
      <div className="flex items-center gap-2">
        <RoleBadge role={message.role} />
        {hasHinglish && (
          <span className="text-[9px] font-semibold text-amber-600 border border-amber-200 bg-amber-50 px-1.5 py-0.5 rounded-full uppercase tracking-wide">
            Hinglish
          </span>
        )}
        {index !== undefined && (
          <span className="text-[10px] text-gray-300 ml-auto font-mono">#{index}</span>
        )}
      </div>
      <p className={cn("text-sm leading-relaxed whitespace-pre-wrap break-words", isSystem ? "italic text-gray-400 text-xs" : textColor)}>
        {message.content}
      </p>
    </div>
  );
}
