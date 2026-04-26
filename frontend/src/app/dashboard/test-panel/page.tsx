"use client";

import { TASK_CONFIG } from "@/lib/constants";
import { TaskCard } from "@/components/dashboard/TaskCard";
import type { TaskName } from "@/types";

const ROUND1_TASKS: TaskName[] = ["easy", "medium", "hard", "nightmare"];
const HIERARCHY_TASKS: TaskName[] = [
  "hierarchy_easy",
  "hierarchy_medium",
  "hierarchy_hard",
];
const CURRICULUM_TASKS: TaskName[] = [
  "curriculum_basic",
  "curriculum_supervisor",
  "curriculum_full_hierarchy",
  "curriculum_nightmare",
];

export default function TestPanelPage() {
  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-base font-semibold text-gray-900">
          Test Panel
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Click any task to start a new session and jump to the demo.
        </p>
      </div>

      <div className="space-y-5">
        <Section title="Round 1 — Single Agent" tasks={ROUND1_TASKS} />
        <Section title="Round 2 — Hierarchical" tasks={HIERARCHY_TASKS} />
        <Section title="Round 2 — Curriculum" tasks={CURRICULUM_TASKS} />
      </div>
    </div>
  );
}

function Section({ title, tasks }: { title: string; tasks: TaskName[] }) {
  return (
    <div className="space-y-2">
      <h2 className="text-[10px] text-gray-400 uppercase tracking-widest">
        {title}
      </h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {tasks.map((t) => (
          <TaskCard key={t} task={t} />
        ))}
      </div>
    </div>
  );
}
