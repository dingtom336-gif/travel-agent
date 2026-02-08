"use client";

import { useCallback, useEffect, useState } from "react";
import type { FaultConfig, Scenario } from "@/lib/simulator-types";
import {
  activateScenario,
  getFaultConfig,
  getScenarios,
  injectFault,
  resetFaults,
} from "@/lib/api-client";

const FAULT_TYPES = [
  { type: "tool_timeout", label: "工具超时", desc: "模拟工具调用超时" },
  { type: "tool_error", label: "工具报错", desc: "模拟工具调用失败" },
  { type: "price_change", label: "价格波动", desc: "随机调整价格数据" },
  { type: "stock_change", label: "库存变化", desc: "模拟库存紧张" },
  { type: "api_rate_limit", label: "API限流", desc: "模拟请求频率限制" },
];

export default function FaultConsole() {
  const [config, setConfig] = useState<FaultConfig | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [cfg, sc] = await Promise.all([getFaultConfig(), getScenarios()]);
      setConfig(cfg);
      setScenarios(sc);
    } catch (e) {
      setMsg(`refresh error: ${e}`);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleActivateScenario = async (name: string) => {
    setLoading(true);
    setMsg("");
    try {
      await activateScenario(name);
      setMsg(`scenario "${name}" activated`);
      await refresh();
    } catch (e) {
      setMsg(`error: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const handleInjectFault = async (faultType: string) => {
    setLoading(true);
    setMsg("");
    try {
      await injectFault(faultType);
      setMsg(`fault "${faultType}" injected`);
      await refresh();
    } catch (e) {
      setMsg(`error: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    setMsg("");
    try {
      const res = await resetFaults();
      setMsg(`reset: cleared ${res.faults_cleared} faults`);
      await refresh();
    } catch (e) {
      setMsg(`error: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const isActive = config && config.fault_count > 0;

  return (
    <div className="space-y-6">
      {/* Status banner */}
      <div
        className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${
          isActive
            ? "border-amber-500/30 bg-amber-500/5"
            : "border-emerald-500/30 bg-emerald-500/5"
        }`}
      >
        <span
          className={`inline-block h-3 w-3 rounded-full ${
            isActive ? "bg-amber-500 animate-pulse" : "bg-emerald-500"
          }`}
        />
        <span className="text-sm font-medium">
          {isActive
            ? `${config?.fault_count} 个故障激活中${config?.active_scenario ? ` (${config.active_scenario})` : ""}`
            : "系统正常 — 无故障激活"}
        </span>
        {isActive && (
          <button
            onClick={handleReset}
            disabled={loading}
            className="ml-auto rounded bg-red-500/10 px-3 py-1 text-xs font-medium text-red-500 hover:bg-red-500/20 transition-colors"
          >
            重置全部
          </button>
        )}
      </div>

      {/* Scenario quick-activate */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-foreground">
          预设场景
        </h3>
        <div className="grid gap-3 sm:grid-cols-3">
          {scenarios.map((sc) => (
            <button
              key={sc.name}
              onClick={() => handleActivateScenario(sc.name)}
              disabled={loading}
              className="group rounded-lg border border-border p-4 text-left hover:border-primary/30 hover:bg-primary/5 transition-all"
            >
              <div className="text-sm font-medium text-foreground group-hover:text-primary">
                {sc.name === "peak_season"
                  ? "旺季涨价"
                  : sc.name === "bad_weather"
                    ? "恶劣天气"
                    : sc.name === "budget_crisis"
                      ? "预算危机"
                      : sc.name}
              </div>
              <div className="mt-1 text-xs text-muted-foreground line-clamp-2">
                {sc.description}
              </div>
              <div className="mt-2 flex gap-1 flex-wrap">
                {sc.fault_types.map((ft) => (
                  <span
                    key={ft}
                    className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                  >
                    {ft}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Individual fault toggles */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-foreground">
          单项故障注入
        </h3>
        <div className="space-y-2">
          {FAULT_TYPES.map((ft) => {
            const active =
              config?.active_faults?.[ft.type]?.enabled ?? false;
            return (
              <div
                key={ft.type}
                className="flex items-center justify-between rounded-lg border border-border px-4 py-3"
              >
                <div>
                  <span className="text-sm font-medium text-foreground">
                    {ft.label}
                  </span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {ft.desc}
                  </span>
                </div>
                <button
                  onClick={() => handleInjectFault(ft.type)}
                  disabled={loading || active}
                  className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                    active
                      ? "bg-amber-500/20 text-amber-500 cursor-default"
                      : "bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary"
                  }`}
                >
                  {active ? "已激活" : "注入"}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Current config JSON */}
      {config && config.fault_count > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-foreground">
            当前配置
          </h3>
          <pre className="max-h-48 overflow-auto rounded-lg bg-muted p-3 text-xs text-muted-foreground">
            {JSON.stringify(config, null, 2)}
          </pre>
        </div>
      )}

      {/* Status message */}
      {msg && (
        <div className="rounded-lg bg-muted px-4 py-2 text-xs text-muted-foreground">
          {msg}
        </div>
      )}
    </div>
  );
}
