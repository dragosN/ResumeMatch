"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CategoryScores } from "@/lib/schemas";

type Props = { scores: CategoryScores };

export function CategoryChart({ scores }: Props) {
  const data = [
    { name: "Technical", value: Math.round(scores.technical) },
    { name: "Experience", value: Math.round(scores.experience) },
    { name: "Domain", value: Math.round(scores.domain) },
    { name: "Soft", value: Math.round(scores.soft) },
  ];

  return (
    <div className="h-48 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fill: "var(--muted)", fontSize: 11 }}
            axisLine={{ stroke: "var(--line)" }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "var(--muted)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "var(--panel)",
              border: "1px solid var(--line)",
              borderRadius: 0,
              fontSize: 12,
            }}
            formatter={(value) => [`${value}/100`, "Score"]}
          />
          <Bar dataKey="value" fill="var(--ink)" radius={[2, 2, 0, 0]} maxBarSize={48} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
