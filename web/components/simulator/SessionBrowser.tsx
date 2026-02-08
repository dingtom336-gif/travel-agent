"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  SessionDetail,
  SessionSummary,
  EvaluationResult,
} from "@/lib/simulator-types";
import {
  evaluateSession,
  getSessionDetail,
  listSessions,
} from "@/lib/api-client";

export default function SessionBrowser() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listSessions().then(setSessions);
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    setSelectedId(id);
    setDetail(null);
    setEvaluation(null);
    setLoading(true);
    try {
      const d = await getSessionDetail(id);
      setDetail(d);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  const handleEvaluate = useCallback(async () => {
    if (!selectedId) return;
    try {
      const res = await evaluateSession(selectedId);
      setEvaluation(res.evaluation);
    } catch {
      // ignore
    }
  }, [selectedId]);

  return (
    <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
      {/* Session list */}
      <div className="rounded-lg border border-border">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-sm font-semibold">会话列表</span>
          <button
            onClick={() => listSessions().then(setSessions)}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            刷新
          </button>
        </div>
        <div className="max-h-[600px] overflow-auto">
          {sessions.length === 0 && (
            <div className="p-4 text-center text-sm text-muted-foreground">
              暂无会话
            </div>
          )}
          {sessions.map((s) => (
            <button
              key={s.session_id}
              onClick={() => loadDetail(s.session_id)}
              className={`w-full border-b border-border px-4 py-3 text-left hover:bg-muted/50 transition-colors ${
                selectedId === s.session_id ? "bg-primary/5" : ""
              }`}
            >
              <div className="text-sm font-medium text-foreground truncate">
                {s.session_id}
              </div>
              <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                <span>{s.message_count} 消息</span>
                <span>{s.trace_count} 追踪</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      <div className="space-y-4">
        {!detail && !loading && (
          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-border text-sm text-muted-foreground">
            选择左侧会话查看详情
          </div>
        )}

        {loading && (
          <div className="flex h-48 items-center justify-center rounded-lg border border-border">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
          </div>
        )}

        {detail && (
          <>
            {/* Header */}
            <div className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
              <div>
                <div className="text-sm font-semibold">{detail.session_id}</div>
                <div className="text-xs text-muted-foreground">
                  {detail.message_count} 消息 | {detail.trace_count} 追踪
                </div>
              </div>
              <button
                onClick={handleEvaluate}
                className="rounded-lg bg-primary px-4 py-1.5 text-xs font-medium text-white hover:bg-primary/90 transition-colors"
              >
                评估
              </button>
            </div>

            {/* Evaluation inline */}
            {evaluation && (
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
                <div className="flex items-center gap-4">
                  <span className="text-2xl font-bold">{evaluation.total_score.toFixed(1)}</span>
                  <div className="flex-1 flex gap-2 flex-wrap">
                    {evaluation.dimension_scores.map((ds) => (
                      <span
                        key={ds.dimension}
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          ds.score >= 4
                            ? "bg-emerald-500/10 text-emerald-600"
                            : ds.score >= 3
                              ? "bg-amber-500/10 text-amber-600"
                              : "bg-red-500/10 text-red-600"
                        }`}
                      >
                        {ds.label.split(" ")[0]} {ds.score}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Messages */}
            <div>
              <h4 className="mb-2 text-sm font-semibold">消息历史</h4>
              <div className="max-h-64 space-y-2 overflow-auto rounded-lg border border-border p-3">
                {detail.messages.map((m, i) => (
                  <div
                    key={i}
                    className={`rounded-lg px-3 py-2 text-sm ${
                      m.role === "user"
                        ? "bg-primary/5 border border-primary/10"
                        : "bg-muted"
                    }`}
                  >
                    <span className="text-xs font-medium text-muted-foreground">
                      {m.role}
                    </span>
                    <p className="mt-1 whitespace-pre-wrap">
                      {m.content.slice(0, 300)}
                      {m.content.length > 300 && "..."}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Traces */}
            {detail.traces.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold">Agent 追踪</h4>
                <div className="overflow-auto rounded-lg border border-border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-muted/50 text-left text-xs text-muted-foreground">
                        <th className="px-3 py-2">Agent</th>
                        <th className="px-3 py-2">任务</th>
                        <th className="px-3 py-2">状态</th>
                        <th className="px-3 py-2">耗时</th>
                        <th className="px-3 py-2">错误</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.traces.map((t, i) => (
                        <tr key={i} className="border-b border-border">
                          <td className="px-3 py-2 font-medium">{t.agent}</td>
                          <td className="px-3 py-2 text-xs text-muted-foreground max-w-[200px] truncate">
                            {t.goal}
                          </td>
                          <td className="px-3 py-2">
                            <span
                              className={`rounded px-1.5 py-0.5 text-xs ${
                                t.status === "success"
                                  ? "bg-emerald-500/10 text-emerald-600"
                                  : "bg-red-500/10 text-red-600"
                              }`}
                            >
                              {t.status}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-xs tabular-nums">
                            {t.duration_ms}ms
                          </td>
                          <td className="px-3 py-2 text-xs text-red-500 max-w-[150px] truncate">
                            {t.error || "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
