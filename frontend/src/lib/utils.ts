import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { HINGLISH_MARKERS } from "./constants";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Converts customer_sentiment [-1, 1] into a [0, 1] frustration level */
export function sentimentToFrustration(sentiment: number): number {
  return Math.max(0, Math.min(1, (1 - sentiment) / 2));
}

export function frustrationLabel(level: number): string {
  if (level < 0.2) return "Calm";
  if (level < 0.4) return "Neutral";
  if (level < 0.6) return "Frustrated";
  if (level < 0.8) return "Agitated";
  return "Furious";
}

export function frustrationColor(level: number): string {
  if (level < 0.2) return "text-green-400";
  if (level < 0.4) return "text-yellow-400";
  if (level < 0.6) return "text-orange-400";
  if (level < 0.8) return "text-orange-500";
  return "text-red-500";
}

export function frustrationBarColor(level: number): string {
  if (level < 0.4) return "bg-green-500";
  if (level < 0.7) return "bg-orange-500";
  return "bg-red-500";
}

export function detectHinglish(text: string): boolean {
  const lower = text.toLowerCase();
  return HINGLISH_MARKERS.some((w) => {
    const regex = new RegExp(`\\b${w}\\b`, "i");
    return regex.test(lower);
  });
}

export function formatScore(val: number): string {
  return `${Math.round(val * 100)}%`;
}

export function roleDisplayName(role: string): string {
  const map: Record<string, string> = {
    support_agent: "Support Agent",
    supervisor: "Supervisor",
    manager: "Manager",
    customer: "Customer",
    agent: "Agent",
    system: "System",
  };
  return map[role] ?? role;
}

export function truncate(str: string, max = 80): string {
  if (str.length <= max) return str;
  return str.slice(0, max) + "…";
}
