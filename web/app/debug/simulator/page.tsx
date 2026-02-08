"use client";

import { useState } from "react";
import PersonaPlayground from "@/components/simulator/PersonaPlayground";
import FaultConsole from "@/components/simulator/FaultConsole";
import EvaluationDashboard from "@/components/simulator/EvaluationDashboard";
import SessionBrowser from "@/components/simulator/SessionBrowser";

const DEBUG_PASSWORD = "travelmind2026";

const TABS = [
  { key: "battle", label: "人格对战" },
  { key: "fault", label: "故障注入" },
  { key: "eval", label: "评估仪表板" },
  { key: "session", label: "会话浏览" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function SimulatorPage() {
  const [authed, setAuthed] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("debug_authed") === "1";
    }
    return false;
  });
  const [password, setPassword] = useState("");
  const [pwError, setPwError] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>("battle");

  const handleLogin = () => {
    if (password === DEBUG_PASSWORD) {
      setAuthed(true);
      localStorage.setItem("debug_authed", "1");
      setPwError(false);
    } else {
      setPwError(true);
    }
  };

  // Password gate
  if (!authed) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="w-full max-w-sm rounded-xl border border-border bg-background p-8 shadow-lg">
          <div className="mb-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
              <svg className="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
              </svg>
            </div>
            <h1 className="text-lg font-bold text-foreground">Debug Console</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              输入管理密码以访问模拟器
            </p>
          </div>
          <div className="space-y-4">
            <input
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setPwError(false);
              }}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              placeholder="管理密码"
              className={`w-full rounded-lg border px-4 py-2.5 text-sm bg-background ${
                pwError ? "border-red-500" : "border-border"
              }`}
            />
            {pwError && (
              <p className="text-xs text-red-500">密码错误</p>
            )}
            <button
              onClick={handleLogin}
              className="w-full rounded-lg bg-primary py-2.5 text-sm font-medium text-white hover:bg-primary/90 transition-colors"
            >
              进入
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold text-foreground">
              TravelMind Debug Console
            </span>
            <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-500">
              INTERNAL
            </span>
          </div>
          <button
            onClick={() => {
              setAuthed(false);
              localStorage.removeItem("debug_authed");
            }}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            退出
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <div className="mx-auto flex max-w-7xl gap-0 px-4">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`border-b-2 px-5 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-7xl px-4 py-6">
        {activeTab === "battle" && <PersonaPlayground />}
        {activeTab === "fault" && <FaultConsole />}
        {activeTab === "eval" && <EvaluationDashboard />}
        {activeTab === "session" && <SessionBrowser />}
      </div>
    </div>
  );
}
