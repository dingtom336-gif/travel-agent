"use client";

import { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import TimelineCard from "@/components/cards/TimelineCard";
import BudgetChart from "@/components/cards/BudgetChart";
import MapWrapper from "@/components/map/MapWrapper";
import { mockItinerary } from "@/lib/mock-itinerary";
import { TimelineDayData } from "@/lib/types";

type TabType = "timeline" | "map" | "budget";

/**
 * Itinerary result page with tab-based views.
 * Route: /itinerary/[id]
 */
export default function ItineraryPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [activeTab, setActiveTab] = useState<TabType>("timeline");
  const [expandedDays, setExpandedDays] = useState<Set<number>>(() => {
    // Expand all days by default
    return new Set(mockItinerary.days.map((d) => d.day));
  });
  const [isSaved, setIsSaved] = useState(false);

  // In production, fetch itinerary by id; for now use mock
  const itinerary = mockItinerary;

  // Compute summary stats
  const summary = useMemo(() => {
    const totalDays = itinerary.days.length;
    const totalActivities = itinerary.days.reduce(
      (sum, d) => sum + d.items.length,
      0
    );
    return { totalDays, totalActivities };
  }, [itinerary]);

  // Toggle day expand/collapse
  const toggleDay = (day: number) => {
    setExpandedDays((prev) => {
      const next = new Set(prev);
      if (next.has(day)) {
        next.delete(day);
      } else {
        next.add(day);
      }
      return next;
    });
  };

  // Expand / collapse all
  const expandAll = () => {
    setExpandedDays(new Set(itinerary.days.map((d) => d.day)));
  };

  const collapseAll = () => {
    setExpandedDays(new Set());
  };

  // Tab definitions
  const tabs: { key: TabType; label: string; icon: React.ReactNode }[] = [
    {
      key: "timeline",
      label: "时间线",
      icon: (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
        </svg>
      ),
    },
    {
      key: "map",
      label: "地图",
      icon: (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
        </svg>
      ),
    },
    {
      key: "budget",
      label: "预算",
      icon: (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-background">
      {/* Header section */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
          {/* Back link */}
          <button
            onClick={() => router.back()}
            className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            返回
          </button>

          {/* Title row */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 flex-1">
              <h1 className="text-2xl font-bold text-foreground sm:text-3xl">
                {itinerary.title}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                {/* Destination */}
                <span className="inline-flex items-center gap-1">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                  </svg>
                  {itinerary.destination}
                </span>
                {/* Date range */}
                <span className="inline-flex items-center gap-1">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                  </svg>
                  {itinerary.startDate} ~ {itinerary.endDate}
                </span>
                {/* Travelers */}
                <span className="inline-flex items-center gap-1">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
                  </svg>
                  {itinerary.travelers} 人
                </span>
              </div>
            </div>

            {/* Status badge */}
            <StatusBadge status={itinerary.status} />
          </div>

          {/* Summary stats */}
          <div className="mt-4 flex flex-wrap gap-4">
            <StatChip label="总天数" value={`${summary.totalDays} 天`} />
            <StatChip label="总活动" value={`${summary.totalActivities} 项`} />
            <StatChip
              label="总预算"
              value={`${itinerary.currency} ${itinerary.totalBudget.toLocaleString()}`}
            />
          </div>
        </div>

        {/* Tab bar */}
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <div className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex items-center gap-1.5 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main content area */}
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        {activeTab === "timeline" && (
          <TimelineView
            days={itinerary.days}
            expandedDays={expandedDays}
            onToggleDay={toggleDay}
            onExpandAll={expandAll}
            onCollapseAll={collapseAll}
          />
        )}
        {activeTab === "map" && <MapWrapper days={itinerary.days} />}
        {activeTab === "budget" && <BudgetChart data={itinerary.budget} />}
      </div>

      {/* Bottom action bar */}
      <ActionBar
        isSaved={isSaved}
        onToggleSave={() => setIsSaved(!isSaved)}
        onShare={() => {
          if (typeof navigator !== "undefined" && navigator.clipboard) {
            navigator.clipboard.writeText(window.location.href);
          }
        }}
        onBackToChat={() => router.push("/chat")}
        itineraryId={id}
      />
    </div>
  );
}

// ----- Sub-components -----

/** Status badge for itinerary status */
function StatusBadge({
  status,
}: {
  status: "draft" | "confirmed" | "in_progress" | "completed";
}) {
  const styles: Record<string, string> = {
    draft: "bg-yellow-100 text-yellow-700",
    confirmed: "bg-green-100 text-green-700",
    in_progress: "bg-blue-100 text-blue-700",
    completed: "bg-gray-100 text-gray-600",
  };
  const labels: Record<string, string> = {
    draft: "草稿",
    confirmed: "已确认",
    in_progress: "进行中",
    completed: "已完成",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

/** Small stat chip */
function StatChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-lg bg-muted px-3 py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold text-card-foreground">
        {value}
      </span>
    </div>
  );
}

/** Timeline view with collapsible day cards */
function TimelineView({
  days,
  expandedDays,
  onToggleDay,
  onExpandAll,
  onCollapseAll,
}: {
  days: TimelineDayData[];
  expandedDays: Set<number>;
  onToggleDay: (day: number) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
}) {
  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-end gap-2">
        <button
          onClick={onExpandAll}
          className="text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          全部展开
        </button>
        <span className="text-xs text-border">|</span>
        <button
          onClick={onCollapseAll}
          className="text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          全部折叠
        </button>
      </div>

      {/* Day cards */}
      {days.map((day) => {
        const isExpanded = expandedDays.has(day.day);
        return (
          <div key={day.day} className="animate-fade-in">
            {/* Collapsed header (always visible) */}
            <button
              onClick={() => onToggleDay(day.day)}
              className="flex w-full items-center gap-3 rounded-xl border border-border bg-card p-4 text-left transition-colors hover:bg-muted/50"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-white">
                D{day.day}
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-semibold text-card-foreground">
                  {day.title}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {day.date} &middot; {day.items.length} 项活动
                </p>
              </div>
              <svg
                className={`h-5 w-5 shrink-0 text-muted-foreground transition-transform duration-200 ${
                  isExpanded ? "rotate-180" : ""
                }`}
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
              </svg>
            </button>

            {/* Expanded content */}
            {isExpanded && (
              <div className="mt-2 animate-fade-in">
                <TimelineCard data={day} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Bottom floating action bar */
function ActionBar({
  isSaved,
  onToggleSave,
  onShare,
  onBackToChat,
  itineraryId,
}: {
  isSaved: boolean;
  onToggleSave: () => void;
  onShare: () => void;
  onBackToChat: () => void;
  itineraryId: string;
}) {
  return (
    <div className="sticky bottom-0 border-t border-border bg-card/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
        {/* Left actions */}
        <div className="flex items-center gap-2">
          {/* Share */}
          <button
            onClick={onShare}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-card-foreground transition-colors hover:bg-muted"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
            </svg>
            <span className="hidden sm:inline">分享</span>
          </button>

          {/* Export PDF */}
          <button
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-card-foreground transition-colors hover:bg-muted"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            <span className="hidden sm:inline">导出 PDF</span>
          </button>

          {/* Save / Bookmark */}
          <button
            onClick={onToggleSave}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition-colors ${
              isSaved
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-card-foreground hover:bg-muted"
            }`}
          >
            <svg
              className="h-4 w-4"
              fill={isSaved ? "currentColor" : "none"}
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
            </svg>
            <span className="hidden sm:inline">
              {isSaved ? "已收藏" : "收藏"}
            </span>
          </button>
        </div>

        {/* Right action - back to chat */}
        <button
          onClick={onBackToChat}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-dark"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
          </svg>
          继续对话优化
        </button>
      </div>
    </div>
  );
}
