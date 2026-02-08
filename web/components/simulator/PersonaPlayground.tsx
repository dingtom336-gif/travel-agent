"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  BattleResult,
  Persona,
  Scenario,
} from "@/lib/simulator-types";
import { getPersonas, getScenarios, runBattle } from "@/lib/api-client";
import RadarChart from "./RadarChart";

export default function PersonaPlayground() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedPersona, setSelectedPersona] = useState("");
  const [selectedScenario, setSelectedScenario] = useState("");
  const [turns, setTurns] = useState(3);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BattleResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getPersonas(), getScenarios()]).then(([p, s]) => {
      setPersonas(p);
      setScenarios(s);
      if (p.length > 0) setSelectedPersona(p[0].name);
    });
  }, []);

  const handleStart = useCallback(async () => {
    if (!selectedPersona) return;
    setRunning(true);
    setResult(null);
    setError("");
    try {
      const res = await runBattle(
        selectedPersona,
        turns,
        selectedScenario || undefined
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }, [selectedPersona, selectedScenario, turns]);

  const personaMap: Record<string, string> = {
    hesitant: "犹豫型",
    price_sensitive: "价格敏感型",
    vague: "模糊型",
    luxury: "奢华型",
    family: "亲子型",
  };

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="grid gap-4 sm:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            用户人格
          </label>
          <select
            value={selectedPersona}
            onChange={(e) => setSelectedPersona(e.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            {personas.map((p) => (
              <option key={p.name} value={p.name}>
                {personaMap[p.name] || p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            场景（可选）
          </label>
          <select
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            <option value="">无</option>
            {scenarios.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name === "peak_season"
                  ? "旺季涨价"
                  : s.name === "bad_weather"
                    ? "恶劣天气"
                    : s.name === "budget_crisis"
                      ? "预算危机"
                      : s.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            对话轮数
          </label>
          <input
            type="number"
            min={1}
            max={10}
            value={turns}
            onChange={(e) => setTurns(Number(e.target.value))}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={handleStart}
            disabled={running || !selectedPersona}
            className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {running ? (
              <span className="flex items-center justify-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                对战中...
              </span>
            ) : (
              "开始对战"
            )}
          </button>
        </div>
      </div>

      {/* Persona info */}
      {selectedPersona && (
        <div className="rounded-lg border border-border bg-muted/30 px-4 py-3">
          <div className="text-xs text-muted-foreground">
            {personas.find((p) => p.name === selectedPersona)?.description}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-500">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Stats row */}
          <div className="grid gap-3 sm:grid-cols-4">
            <StatCard
              label="总分"
              value={result.evaluation.total_score.toFixed(1)}
              sub="/5.0"
            />
            <StatCard
              label="完成轮数"
              value={String(result.turns_completed)}
              sub={`/${turns} 轮`}
            />
            <StatCard
              label="总耗时"
              value={`${(result.total_duration_ms / 1000).toFixed(1)}`}
              sub="秒"
            />
            <StatCard
              label="Agent 调用"
              value={String(result.traces.length)}
              sub="次"
            />
          </div>

          {/* Radar chart + dimension details */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="flex items-center justify-center rounded-lg border border-border p-4">
              <RadarChart scores={result.evaluation.dimension_scores} />
            </div>
            <div className="space-y-2">
              {result.evaluation.dimension_scores.map((ds) => (
                <div
                  key={ds.dimension}
                  className="flex items-center gap-3 rounded-lg border border-border px-4 py-2"
                >
                  <div className="min-w-[80px] text-sm font-medium">
                    {ds.label.split(" ")[0]}
                  </div>
                  <div className="flex-1">
                    <div className="h-2 rounded-full bg-muted">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          ds.score >= 4
                            ? "bg-emerald-500"
                            : ds.score >= 3
                              ? "bg-amber-500"
                              : "bg-red-500"
                        }`}
                        style={{ width: `${(ds.score / 5) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-sm font-bold tabular-nums">
                    {ds.score}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Suggestions */}
          {result.evaluation.suggestions.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">改进建议</h3>
              <ul className="space-y-1">
                {result.evaluation.suggestions.map((s, i) => (
                  <li
                    key={i}
                    className="rounded-lg bg-amber-500/5 border border-amber-500/20 px-3 py-2 text-xs text-muted-foreground"
                  >
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Conversation */}
          <div>
            <h3 className="mb-2 text-sm font-semibold">对话记录</h3>
            <div className="max-h-96 space-y-2 overflow-auto rounded-lg border border-border p-3">
              {result.messages.map((m, i) => (
                <div
                  key={i}
                  className={`rounded-lg px-3 py-2 text-sm ${
                    m.role === "user"
                      ? "bg-primary/5 border border-primary/10"
                      : "bg-muted"
                  }`}
                >
                  <span className="text-xs font-medium text-muted-foreground">
                    {m.role === "user" ? "User" : "Assistant"}
                  </span>
                  <p className="mt-1 whitespace-pre-wrap text-foreground">
                    {m.content.slice(0, 500)}
                    {m.content.length > 500 && "..."}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="rounded-lg border border-border p-4 text-center">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-bold text-foreground">
        {value}
        <span className="text-sm font-normal text-muted-foreground">
          {sub}
        </span>
      </div>
    </div>
  );
}
