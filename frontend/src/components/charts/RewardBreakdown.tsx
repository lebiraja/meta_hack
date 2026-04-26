"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { REWARD_CHART_KEYS } from "@/lib/constants";
import { formatScore } from "@/lib/utils";
import type { Reward } from "@/types";

interface Props { reward: Reward; }

export function RewardBreakdown({ reward }: Props) {
  const data = REWARD_CHART_KEYS.map(({ key, label, color }) => ({
    name: label,
    value: Math.max(0, Math.min(1, (reward as unknown as Record<string, number>)[key] ?? 0)),
    fill: color,
  }));

  return (
    <div className="w-full space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold">Reward Breakdown</span>
        <span className="text-sm font-mono font-bold text-indigo-600">{formatScore(reward.value)}</span>
      </div>
      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 16, top: 0, bottom: 0 }}>
          <XAxis type="number" domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
            tick={{ fontSize: 9, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" width={62}
            tick={{ fontSize: 9, fill: "#6b7280" }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              fontSize: 11,
              boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
            }}
            labelStyle={{ color: "#111827" }}
            formatter={(val) => [`${Math.round((val as number) * 100)}%`, ""]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={10}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
