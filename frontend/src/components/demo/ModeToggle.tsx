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
    <div className="flex items-center gap-1 border border-gray-200 rounded-xl p-0.5 bg-gray-50">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          title={tab.description}
          className={cn(
            "px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200",
            mode === tab.id
              ? "bg-white text-gray-900 shadow-sm border border-gray-200"
              : "text-gray-400 hover:text-gray-600"
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
