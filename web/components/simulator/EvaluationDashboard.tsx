"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  EvaluationResult,
  SessionSummary,
} from "@/lib/simulator-types";
import { evaluateSession, listSessions } from "@/lib/api-client";
import RadarChart from "./RadarChart";

export default function EvaluationDashboard() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listSessions().then((s) => {
      setSessions(s);
      if (s.length > 0) setSelectedSession(s[0].session_id);
    });
  }, []);

  const handleEvaluate = useCallback(async () => {
    if (!selectedSession) return;
    setEvaluating(true);
    setResult(null);
    setError("");
    try {
      const res = await evaluateSession(selectedSession);
      setResult(res.evaluation);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setEvaluating(false);
    }
  }, [selectedSession]);

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-end gap-4">
        <div className="flex-1">
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            选择会话
          </label>
          <select
            value={selectedSession}
            onChange={(e) => setSelectedSession(e.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            {sessions.length === 0 && (
              <option value="">暂无会话</option>
            )}
            {sessions.map((s) => (
              <option key={s.session_id} value={s.session_id}>
                {s.session_id} ({s.message_count} 消息, {s.trace_count}{" "}
                追踪)
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleEvaluate}
          disabled={evaluating || !selectedSession}
          className="rounded-lg bg-primary px-6 py-2 text-sm font-medium text-white hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {evaluating ? "评估中..." : "执行评估"}
        </button>
        <button
          onClick={() => listSessions().then(setSessions)}
          className="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted transition-colors"
        >
          刷新
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-500">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-6">
          {/* Total score */}
          <div className="flex items-center justify-center gap-8 rounded-lg border border-border p-6">
            <div className="text-center">
              <div className="text-5xl font-bold text-foreground">
                {result.total_score.toFixed(1)}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                总分 / 5.0
              </div>
            </div>
            <RadarChart scores={result.dimension_scores} size={240} />
          </div>

          {/* Dimension progress bars */}
          <div className="space-y-3">
            {result.dimension_scores.map((ds) => (
              <div
                key={ds.dimension}
                className="rounded-lg border border-border p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{ds.label}</span>
                  <span
                    className={`text-sm font-bold ${
                      ds.score >= 4
                        ? "text-emerald-500"
                        : ds.score >= 3
                          ? "text-amber-500"
                          : "text-red-500"
                    }`}
                  >
                    {ds.score}/5
                  </span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-muted">
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
                <div className="mt-2 text-xs text-muted-foreground">
                  {ds.reason}
                </div>
              </div>
            ))}
          </div>

          {/* Suggestions */}
          {result.suggestions.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">改进建议</h3>
              <ul className="space-y-1">
                {result.suggestions.map((s, i) => (
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
        </div>
      )}
    </div>
  );
}
