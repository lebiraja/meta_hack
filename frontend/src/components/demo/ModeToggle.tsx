import { cn } from "@/lib/utils";

export type DemoMode = "auto" | "customer" | "manual";

interface Props {
  mode: DemoMode;
  onChange: (mode: DemoMode) => void;
}

const TABS: { id: DemoMode; label: string; description: string }[] = [
  {
    id: "auto",
    label: "Auto-Play",
    description: "Watch AI agents handle the ticket",
  },
  {
    id: "customer",
    label: "Chat as Customer",
    description: "Type as the customer, AI responds",
  },
  {
    id: "manual",
    label: "Manual Agent",
    description: "You control the agent actions",
  },
];

export function ModeToggle({ mode, onChange }: Props) {
  return (
    <div className="flex items-center gap-1 border border-neutral-800 rounded-lg p-0.5 bg-neutral-900">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          title={tab.description}
          className={cn(
            "px-3 py-1.5 rounded text-xs font-medium transition-colors",
            mode === tab.id
              ? "bg-neutral-800 text-neutral-100"
              : "text-neutral-500 hover:text-neutral-300"
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
