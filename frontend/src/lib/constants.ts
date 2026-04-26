import type { TaskName, Priority } from "@/types";

export const TASK_CONFIG: Record<
  TaskName,
  {
    label: string;
    maxSteps: number;
    levels: number[];
    driftProbability: number;
    difficulty: "easy" | "medium" | "hard" | "nightmare";
    hierarchical: boolean;
    hinglishEnabled: boolean;
    description: string;
  }
> = {
  easy: { label: "Easy", maxSteps: 5, levels: [1], driftProbability: 0, difficulty: "easy", hierarchical: false, hinglishEnabled: false, description: "Billing FAQ — single agent, no drift" },
  medium: { label: "Medium", maxSteps: 8, levels: [1], driftProbability: 0, difficulty: "medium", hierarchical: false, hinglishEnabled: false, description: "Multi-turn complaint — single agent" },
  hard: { label: "Hard", maxSteps: 10, levels: [1], driftProbability: 0, difficulty: "hard", hierarchical: false, hinglishEnabled: false, description: "SLA escalation — must escalate early" },
  nightmare: { label: "Nightmare", maxSteps: 12, levels: [1], driftProbability: 0, difficulty: "nightmare", hierarchical: false, hinglishEnabled: false, description: "Multi-issue — complex prioritization" },
  hierarchy_easy: { label: "Hierarchy Easy", maxSteps: 8, levels: [1, 2], driftProbability: 0.3, difficulty: "easy", hierarchical: true, hinglishEnabled: false, description: "L1 + L2 supervisor review, 30% drift" },
  hierarchy_medium: { label: "Hierarchy Medium", maxSteps: 12, levels: [1, 2], driftProbability: 0.5, difficulty: "medium", hierarchical: true, hinglishEnabled: false, description: "L1 + L2 supervisor, 50% policy drift" },
  hierarchy_hard: { label: "Hierarchy Hard", maxSteps: 15, levels: [1, 2, 3], driftProbability: 0.8, difficulty: "hard", hierarchical: true, hinglishEnabled: false, description: "Full L1+L2+L3 hierarchy, 80% drift" },
  curriculum_basic: { label: "Curriculum: Basic", maxSteps: 6, levels: [1], driftProbability: 0, difficulty: "easy", hierarchical: true, hinglishEnabled: false, description: "Stage 1 — learn empathy & resolution" },
  curriculum_supervisor: { label: "Curriculum: Supervisor", maxSteps: 10, levels: [1, 2], driftProbability: 0.2, difficulty: "medium", hierarchical: true, hinglishEnabled: false, description: "Stage 2 — learn feedback incorporation" },
  curriculum_full_hierarchy: { label: "Curriculum: Full Hierarchy", maxSteps: 14, levels: [1, 2, 3], driftProbability: 0.8, difficulty: "hard", hierarchical: true, hinglishEnabled: false, description: "Stage 3 — full 3-level coordination" },
  curriculum_nightmare: { label: "Curriculum: Nightmare", maxSteps: 18, levels: [1, 2, 3], driftProbability: 1.0, difficulty: "nightmare", hierarchical: true, hinglishEnabled: true, description: "Stage 4 — adversarial + Hinglish" },
  multi_domain: { label: "Multi-Domain (DB)", maxSteps: 8, levels: [1], driftProbability: 0, difficulty: "hard", hierarchical: true, hinglishEnabled: false, description: "Query user/order DB, cite grounded data, avoid hallucination" },
};

export const DIFFICULTY_COLORS = {
  easy: "text-emerald-700 border-emerald-200 bg-emerald-50",
  medium: "text-amber-700 border-amber-200 bg-amber-50",
  hard: "text-orange-700 border-orange-200 bg-orange-50",
  nightmare: "text-red-700 border-red-200 bg-red-50",
} as const;

export const ROLE_TEXT_COLORS: Record<string, string> = {
  customer: "text-slate-600",
  agent: "text-indigo-600",
  support_agent: "text-indigo-600",
  supervisor: "text-amber-600",
  manager: "text-rose-600",
  system: "text-gray-400",
};

export const ROLE_BG_COLORS: Record<string, string> = {
  customer: "bg-slate-50",
  agent: "bg-indigo-50",
  support_agent: "bg-indigo-50",
  supervisor: "bg-amber-50",
  manager: "bg-rose-50",
  system: "bg-gray-50",
};

export const ROLE_BORDER_COLORS: Record<string, string> = {
  customer: "border-slate-200",
  agent: "border-indigo-200",
  support_agent: "border-indigo-200",
  supervisor: "border-amber-200",
  manager: "border-rose-200",
  system: "border-gray-200",
};

export const PRIORITY_COLORS: Record<Priority, string> = {
  low: "text-emerald-700 border-emerald-200 bg-emerald-50",
  medium: "text-amber-700 border-amber-200 bg-amber-50",
  high: "text-orange-700 border-orange-200 bg-orange-50",
  critical: "text-red-700 border-red-200 bg-red-50",
};

export const HINGLISH_MARKERS = [
  "nahi", "nahin", "hai", "karo", "mera", "meri", "aapka", "kyun", "kya",
  "abhi", "bilkul", "theek", "zyada", "bahut", "sab", "kuch", "bhai", "yaar",
  "bolo", "dekho", "samajh", "matlab", "arey", "arre", "kitna", "lagega", "karo", "please",
];

export const REWARD_CHART_KEYS = [
  { key: "resolution_score", label: "Resolution", color: "#6366f1" },
  { key: "tone_score", label: "Tone", color: "#8b5cf6" },
  { key: "efficiency_score", label: "Efficiency", color: "#06b6d4" },
  { key: "accuracy_score", label: "Accuracy", color: "#10b981" },
  { key: "empathy_score", label: "Empathy", color: "#f59e0b" },
  { key: "policy_adherence_score", label: "Policy", color: "#f97316" },
  { key: "oversight_score", label: "Oversight", color: "#ec4899" },
  { key: "decision_quality_score", label: "Decision", color: "#14b8a6" },
] as const;

export const ROLE_DISPLAY_NAMES: Record<string, string> = {
  support_agent: "Support Agent",
  supervisor: "Supervisor",
  manager: "Manager",
};
