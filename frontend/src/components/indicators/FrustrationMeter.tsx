import {
  sentimentToFrustration,
  frustrationLabel,
  frustrationColor,
  frustrationBarColor,
  cn,
} from "@/lib/utils";

interface Props {
  sentiment: number;
  trajectory?: number[];
}

export function FrustrationMeter({ sentiment, trajectory = [] }: Props) {
  const level = sentimentToFrustration(sentiment);
  const label = frustrationLabel(level);
  const colorClass = frustrationColor(level);
  const barColor = frustrationBarColor(level);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-neutral-500">Customer Mood</span>
        <span className={cn("text-xs font-medium", colorClass)}>{label}</span>
      </div>
      <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", barColor)}
          style={{ width: `${Math.round(level * 100)}%` }}
        />
      </div>
      {trajectory.length > 1 && (
        <div className="flex gap-0.5 items-end h-4">
          {trajectory.slice(-10).map((s, i) => {
            const h = Math.round(sentimentToFrustration(s) * 14);
            return (
              <div
                key={i}
                className="flex-1 rounded-sm bg-neutral-700"
                style={{ height: `${Math.max(2, h)}px` }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
