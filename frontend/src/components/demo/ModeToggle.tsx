import { cn } from "@/lib/utils";

export type DemoMode = "auto" | "customer";

interface Props {
  mode: DemoMode;
  onChange: (mode: DemoMode) => void;
}

const TABS: { id: DemoMode; label: string; description: string }[] = [
  {
    id: "auto",
    label: "Auto-Play",
    description: "Watch AI agents handle the ticket automatically",
  },
  {
    id: "customer",
    label: "Chat as Customer",
    description: "Type as the customer, AI agent responds",
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
            "px-4 py-1.5 rounded-md text-xs font-medium transition-all duration-200",
            mode === tab.id
              ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/20"
              : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
