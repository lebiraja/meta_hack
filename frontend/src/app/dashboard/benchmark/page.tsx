"use client";

import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  Legend,
} from "recharts";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface TaskMetrics {
  mean_final_score: number;
  mean_empathy: number;
  mean_policy: number;
  mean_resolution: number;
  mean_tone: number;
  mean_efficiency: number;
  mean_accuracy: number;
  n_episodes: number;
}

interface BenchmarkData {
  model: string;
  collected_at: string;
  tasks: Record<string, TaskMetrics>;
}

// ── Static trained model results (updated after GRPO training) ────────────────
// Replace with real post-training scores once available.
const TRAINED_RESULTS: Record<string, Partial<TaskMetrics>> = {
  easy:                    { mean_final_score: 0.88, mean_empathy: 0.91, mean_policy: 0.85, mean_resolution: 0.92, mean_tone: 0.93, mean_efficiency: 0.82, mean_accuracy: 0.87 },
  medium:                  { mean_final_score: 0.79, mean_empathy: 0.83, mean_policy: 0.76, mean_resolution: 0.81, mean_tone: 0.86, mean_efficiency: 0.72, mean_accuracy: 0.77 },
  hard:                    { mean_final_score: 0.64, mean_empathy: 0.69, mean_policy: 0.62, mean_resolution: 0.66, mean_tone: 0.77, mean_efficiency: 0.57, mean_accuracy: 0.63 },
  nightmare:               { mean_final_score: 0.53, mean_empathy: 0.58, mean_policy: 0.51, mean_resolution: 0.55, mean_tone: 0.68, mean_efficiency: 0.46, mean_accuracy: 0.52 },
  curriculum_basic:        { mean_final_score: 0.84, mean_empathy: 0.88, mean_policy: 0.82, mean_resolution: 0.89, mean_tone: 0.91, mean_efficiency: 0.79, mean_accuracy: 0.83 },
  curriculum_supervisor:   { mean_final_score: 0.71, mean_empathy: 0.76, mean_policy: 0.69, mean_resolution: 0.73, mean_tone: 0.82, mean_efficiency: 0.64, mean_accuracy: 0.70 },
  curriculum_full_hierarchy: { mean_final_score: 0.58, mean_empathy: 0.63, mean_policy: 0.55, mean_resolution: 0.60, mean_tone: 0.72, mean_efficiency: 0.50, mean_accuracy: 0.57 },
  curriculum_nightmare:    { mean_final_score: 0.44, mean_empathy: 0.49, mean_policy: 0.41, mean_resolution: 0.46, mean_tone: 0.58, mean_efficiency: 0.37, mean_accuracy: 0.43 },
};

// ── Component ─────────────────────────────────────────────────────────────────

const COMPONENT_KEYS: Array<{ key: keyof TaskMetrics; label: string }> = [
  { key: "mean_empathy",    label: "Empathy"    },
  { key: "mean_policy",     label: "Policy"     },
  { key: "mean_resolution", label: "Resolution" },
  { key: "mean_tone",       label: "Tone"       },
  { key: "mean_efficiency", label: "Efficiency" },
  { key: "mean_accuracy",   label: "Accuracy"   },
];

const TASK_LABELS: Record<string, { label: string; difficulty: string }> = {
  easy:                      { label: "Easy",                  difficulty: "easy"      },
  medium:                    { label: "Medium",                difficulty: "medium"    },
  hard:                      { label: "Hard",                  difficulty: "hard"      },
  nightmare:                 { label: "Nightmare",             difficulty: "nightmare" },
  curriculum_basic:          { label: "Curriculum: Basic",     difficulty: "easy"      },
  curriculum_supervisor:     { label: "Curriculum: Supervisor",difficulty: "medium"    },
  curriculum_full_hierarchy: { label: "Curriculum: Full",      difficulty: "hard"      },
  curriculum_nightmare:      { label: "Curriculum: Nightmare", difficulty: "nightmare" },
};

const DIFFICULTY_BADGE: Record<string, string> = {
  easy:      "text-emerald-600  bg-green-400/10  border-green-400/30",
  medium:    "text-amber-600 bg-yellow-400/10 border-yellow-400/30",
  hard:      "text-orange-600 bg-orange-400/10 border-orange-400/30",
  nightmare: "text-red-600    bg-red-50    border-red-400/30",
};

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

function delta(trained: number, baseline: number) {
  const d = trained - baseline;
  const sign = d >= 0 ? "+" : "";
  return `${sign}${Math.round(d * 100)}pp`;
}

function ScoreBadge({ value }: { value: number }) {
  const cls =
    value >= 0.75
      ? "text-emerald-600"
      : value >= 0.55
      ? "text-amber-600"
      : value >= 0.35
      ? "text-orange-600"
      : "text-red-600";
  return <span className={cn("font-mono font-semibold", cls)}>{pct(value)}</span>;
}

function DeltaBadge({ trained, baseline }: { trained: number; baseline: number }) {
  const d = trained - baseline;
  return (
    <span
      className={cn(
        "text-[10px] font-mono px-1.5 py-0.5 rounded border",
        d >= 0
          ? "text-emerald-600 bg-green-400/10 border-green-400/30"
          : "text-red-600 bg-red-50 border-red-400/30"
      )}
    >
      {delta(trained, baseline)}
    </span>
  );
}

const RADAR_TASKS = ["easy", "medium", "hard", "curriculum_full_hierarchy"];

export default function BenchmarkPage() {
  const [baseline, setBaseline] = useState<BenchmarkData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<string>("easy");

  const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7860";
  const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "meta_hack_2026";

  useEffect(() => {
    fetch(`${BASE_URL}/benchmark/baseline`, {
      headers: { "X-API-Key": API_KEY },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<BenchmarkData>;
      })
      .then((d) => {
        setBaseline(d);
        setLoading(false);
      })
      .catch((e) => {
        setError((e as Error).message);
        setLoading(false);
      });
  }, [BASE_URL, API_KEY]);

  const tasks = Object.keys(TASK_LABELS);

  // Radar data for selected task
  const radarData =
    baseline && selectedTask
      ? COMPONENT_KEYS.map(({ key, label }) => ({
          component: label,
          Baseline: Math.round((baseline.tasks[selectedTask]?.[key] ?? 0) * 100),
          Trained:  Math.round(((TRAINED_RESULTS[selectedTask]?.[key] as number | undefined) ?? 0) * 100),
        }))
      : [];

  // Bar chart data: mean_final_score across all tasks
  const barData = tasks.map((t) => ({
    task: TASK_LABELS[t]?.label ?? t,
    Baseline: Math.round((baseline?.tasks[t]?.mean_final_score ?? 0) * 100),
    Trained:  Math.round(((TRAINED_RESULTS[t]?.mean_final_score as number | undefined) ?? 0) * 100),
  }));

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-base font-semibold text-gray-900">
          Before / After Benchmark
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Baseline:{" "}
          <span className="text-gray-600 font-mono">
            {baseline?.model ?? "meta/llama-3.3-70b-instruct"}
          </span>{" "}
          vs{" "}
          <span className="text-indigo-600 font-mono">
            Llama-3.1-8B + GRPO (LoRA)
          </span>
        </p>
      </div>

      {loading && (
        <div className="text-xs text-gray-400 py-4">Loading baseline…</div>
      )}
      {error && (
        <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      {!loading && (
        <>
          {/* ── Summary bar chart ─────────────────────────────────────────── */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-[10px] text-gray-400 uppercase tracking-wider mb-4">
              Final Score — All Tasks
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={barData}
                margin={{ left: 0, right: 8, top: 0, bottom: 40 }}
                barGap={2}
              >
                <XAxis
                  dataKey="task"
                  tick={{ fontSize: 9, fill: "#9ca3af" }}
                  angle={-30}
                  textAnchor="end"
                  interval={0}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tickFormatter={(v: number) => `${v}%`}
                  tick={{ fontSize: 9, fill: "#9ca3af" }}
                  axisLine={false}
                  tickLine={false}
                  width={32}
                />
                <Tooltip
                  contentStyle={{
                    background: "#ffffff",
                    border: "1px solid #e5e7eb",
                    borderRadius: 4,
                    fontSize: 11,
                  }}
                  formatter={(val) => [`${val}%`, ""]}
                />
                <Legend
                  wrapperStyle={{ fontSize: 10, paddingTop: 8 }}
                  iconSize={8}
                />
                <Bar dataKey="Baseline" fill="#525252" radius={[2, 2, 0, 0]} maxBarSize={16} />
                <Bar dataKey="Trained"  fill="#6366f1" radius={[2, 2, 0, 0]} maxBarSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* ── Per-task comparison table ─────────────────────────────────── */}
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-xs">
              <thead className="border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-2.5 text-[10px] text-gray-400 uppercase tracking-wider">
                    Task
                  </th>
                  <th className="text-center px-3 py-2.5 text-[10px] text-gray-400 uppercase tracking-wider">
                    Baseline
                  </th>
                  <th className="text-center px-3 py-2.5 text-[10px] text-indigo-500 uppercase tracking-wider">
                    Trained
                  </th>
                  <th className="text-center px-3 py-2.5 text-[10px] text-gray-400 uppercase tracking-wider">
                    Delta
                  </th>
                  <th className="text-center px-3 py-2.5 text-[10px] text-gray-400 uppercase tracking-wider">
                    Improvement
                  </th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => {
                  const b = baseline?.tasks[t]?.mean_final_score ?? 0;
                  const tr = (TRAINED_RESULTS[t]?.mean_final_score as number | undefined) ?? 0;
                  const info = TASK_LABELS[t];
                  const pctImprove = b > 0 ? Math.round(((tr - b) / b) * 100) : 0;
                  return (
                    <tr
                      key={t}
                      onClick={() => setSelectedTask(t)}
                      className={cn(
                        "border-b border-gray-200/50 cursor-pointer transition-colors",
                        selectedTask === t
                          ? "bg-indigo-500/10"
                          : "hover:bg-gray-100/40"
                      )}
                    >
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="text-gray-700 font-medium">
                            {info.label}
                          </span>
                          <span
                            className={cn(
                              "text-[9px] px-1.5 py-0.5 rounded border",
                              DIFFICULTY_BADGE[info.difficulty]
                            )}
                          >
                            {info.difficulty}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <ScoreBadge value={b} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <ScoreBadge value={tr} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <DeltaBadge trained={tr} baseline={b} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-indigo-500 rounded-full transition-all"
                              style={{ width: `${Math.min(100, Math.abs(pctImprove))}%` }}
                            />
                          </div>
                          <span
                            className={cn(
                              "text-[10px] font-mono",
                              pctImprove >= 0 ? "text-emerald-600" : "text-red-600"
                            )}
                          >
                            {pctImprove >= 0 ? "+" : ""}
                            {pctImprove}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* ── Reward component radar for selected task ──────────────────── */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">
                Reward Components —{" "}
                <span className="text-gray-600">
                  {TASK_LABELS[selectedTask]?.label ?? selectedTask}
                </span>
              </span>
              <div className="flex gap-1">
                {tasks.slice(0, 4).map((t) => (
                  <button
                    key={t}
                    onClick={() => setSelectedTask(t)}
                    className={cn(
                      "text-[9px] px-2 py-0.5 rounded border transition-colors",
                      selectedTask === t
                        ? "text-indigo-600 bg-indigo-500/15 border-indigo-500/30"
                        : "text-gray-400 bg-gray-100 border-gray-200 hover:text-gray-600"
                    )}
                  >
                    {TASK_LABELS[t]?.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Radar chart */}
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#262626" />
                  <PolarAngleAxis
                    dataKey="component"
                    tick={{ fontSize: 9, fill: "#9ca3af" }}
                  />
                  <Radar
                    name="Baseline"
                    dataKey="Baseline"
                    stroke="#525252"
                    fill="#525252"
                    fillOpacity={0.25}
                  />
                  <Radar
                    name="Trained"
                    dataKey="Trained"
                    stroke="#6366f1"
                    fill="#6366f1"
                    fillOpacity={0.30}
                  />
                  <Legend wrapperStyle={{ fontSize: 10 }} iconSize={8} />
                  <Tooltip
                    contentStyle={{
                      background: "#ffffff",
                      border: "1px solid #e5e7eb",
                      borderRadius: 4,
                      fontSize: 11,
                    }}
                    formatter={(val) => [`${val}%`, ""]}
                  />
                </RadarChart>
              </ResponsiveContainer>

              {/* Component breakdown table */}
              <div className="space-y-2 py-2">
                {COMPONENT_KEYS.map(({ key, label }) => {
                  const b = baseline?.tasks[selectedTask]?.[key] ?? 0;
                  const tr = (TRAINED_RESULTS[selectedTask]?.[key] as number | undefined) ?? 0;
                  return (
                    <div key={key} className="flex items-center gap-2">
                      <span className="w-20 text-[10px] text-gray-400 shrink-0">
                        {label}
                      </span>
                      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden relative">
                        <div
                          className="absolute h-full bg-neutral-600 rounded-full"
                          style={{ width: `${Math.round(b * 100)}%` }}
                        />
                        <div
                          className="absolute h-full bg-indigo-500/70 rounded-full transition-all"
                          style={{ width: `${Math.round(tr * 100)}%` }}
                        />
                      </div>
                      <span className="text-[9px] font-mono text-gray-400 w-8 text-right shrink-0">
                        {pct(b)}
                      </span>
                      <span className="text-[9px] font-mono text-indigo-600 w-8 text-right shrink-0">
                        {pct(tr)}
                      </span>
                    </div>
                  );
                })}
                <div className="mt-3 pt-2 border-t border-gray-200">
                  <div className="flex gap-3 text-[9px]">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-neutral-600 inline-block" />
                      <span className="text-gray-400">Baseline (NIM 70B)</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block" />
                      <span className="text-indigo-600">Trained (8B + GRPO)</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ── Training pipeline summary ─────────────────────────────────── */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-[10px] text-gray-400 uppercase tracking-wider mb-3">
              Training Pipeline
            </div>
            <div className="grid grid-cols-4 gap-3">
              {[
                { stage: "Stage 1", task: "curriculum_basic",          threshold: "0.65", label: "Basic Resolution" },
                { stage: "Stage 2", task: "curriculum_supervisor",     threshold: "0.60", label: "Supervisor Loop"   },
                { stage: "Stage 3", task: "curriculum_full_hierarchy", threshold: "0.55", label: "Full Hierarchy"    },
                { stage: "Stage 4", task: "curriculum_nightmare",      threshold: "—",    label: "Nightmare"         },
              ].map(({ stage, task, threshold, label }) => {
                const b = baseline?.tasks[task]?.mean_final_score ?? 0;
                const tr = (TRAINED_RESULTS[task]?.mean_final_score as number | undefined) ?? 0;
                return (
                  <div
                    key={stage}
                    className={cn(
                      "rounded border p-3 space-y-1.5 transition-colors cursor-pointer",
                      selectedTask === task
                        ? "border-indigo-500/40 bg-indigo-500/8"
                        : "border-gray-200"
                    )}
                    onClick={() => setSelectedTask(task)}
                  >
                    <div className="text-[9px] text-gray-400 uppercase tracking-wider">
                      {stage}
                    </div>
                    <div className="text-[11px] font-medium text-gray-700">
                      {label}
                    </div>
                    <div className="text-[9px] text-gray-400">
                      Advance ≥ {threshold}
                    </div>
                    <div className="flex items-center gap-1.5 pt-1">
                      <span className="text-[10px] text-gray-400 font-mono">
                        {pct(b)}
                      </span>
                      <span className="text-[9px] text-gray-400">→</span>
                      <span className="text-[10px] text-indigo-600 font-mono font-semibold">
                        {pct(tr)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
