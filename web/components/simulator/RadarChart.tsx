"use client";

import type { DimensionScore } from "@/lib/simulator-types";

// Dimension labels in Chinese
const LABELS: Record<string, string> = {
  intent_understanding: "意图理解",
  tool_usage: "工具调用",
  response_quality: "回答质量",
  personalization: "个性化",
  completeness: "完整性",
  coherence: "连贯性",
};

interface RadarChartProps {
  scores: DimensionScore[];
  size?: number;
}

export default function RadarChart({ scores, size = 280 }: RadarChartProps) {
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size * 0.38;
  const n = scores.length || 6;
  const angleStep = (2 * Math.PI) / n;

  // Get (x, y) for a dimension at given radius
  const getPoint = (index: number, r: number) => ({
    x: cx + r * Math.sin(index * angleStep),
    y: cy - r * Math.cos(index * angleStep),
  });

  // Build polygon path for scores (normalized to 0-5)
  const scorePath = scores
    .map((s, i) => {
      const r = (s.score / 5) * maxR;
      const p = getPoint(i, r);
      return `${i === 0 ? "M" : "L"}${p.x},${p.y}`;
    })
    .join(" ");

  // Grid rings at 1, 2, 3, 4, 5
  const rings = [1, 2, 3, 4, 5];

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="mx-auto"
    >
      {/* Grid rings */}
      {rings.map((ring) => {
        const r = (ring / 5) * maxR;
        const pts = Array.from({ length: n }, (_, i) => {
          const p = getPoint(i, r);
          return `${p.x},${p.y}`;
        }).join(" ");
        return (
          <polygon
            key={ring}
            points={pts}
            fill="none"
            stroke="currentColor"
            strokeWidth={ring === 5 ? 1 : 0.5}
            className="text-muted-foreground/20"
          />
        );
      })}

      {/* Axis lines */}
      {scores.map((_, i) => {
        const p = getPoint(i, maxR);
        return (
          <line
            key={`axis-${i}`}
            x1={cx}
            y1={cy}
            x2={p.x}
            y2={p.y}
            stroke="currentColor"
            strokeWidth={0.5}
            className="text-muted-foreground/20"
          />
        );
      })}

      {/* Score polygon */}
      {scores.length > 0 && (
        <>
          <polygon
            points={scores
              .map((s, i) => {
                const r = (s.score / 5) * maxR;
                const p = getPoint(i, r);
                return `${p.x},${p.y}`;
              })
              .join(" ")}
            fill="hsl(var(--primary) / 0.15)"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
          />
          {/* Score dots */}
          {scores.map((s, i) => {
            const r = (s.score / 5) * maxR;
            const p = getPoint(i, r);
            return (
              <circle
                key={`dot-${i}`}
                cx={p.x}
                cy={p.y}
                r={3}
                fill="hsl(var(--primary))"
              />
            );
          })}
        </>
      )}

      {/* Labels */}
      {scores.map((s, i) => {
        const p = getPoint(i, maxR + 24);
        const label = LABELS[s.dimension] || s.dimension;
        return (
          <text
            key={`label-${i}`}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-muted-foreground text-[11px]"
          >
            {label}
          </text>
        );
      })}

      {/* Score values */}
      {scores.map((s, i) => {
        const p = getPoint(i, maxR + 38);
        return (
          <text
            key={`val-${i}`}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-foreground text-[11px] font-bold"
          >
            {s.score}
          </text>
        );
      })}
    </svg>
  );
}
