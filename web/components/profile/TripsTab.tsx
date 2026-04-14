"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { TripItem } from "@/lib/mock-profile";

// Status label & style map
const statusMap: Record<
  TripItem["status"],
  { label: string; className: string }
> = {
  draft: {
    label: "草稿",
    className: "bg-secondary/10 text-secondary",
  },
  confirmed: {
    label: "已确认",
    className: "bg-primary/10 text-primary",
  },
  in_progress: {
    label: "进行中",
    className: "bg-primary/10 text-primary",
  },
  completed: {
    label: "已完成",
    className: "bg-primary/10 text-primary",
  },
};

// Destination placeholder colors (deterministic by index)
const placeholderColors = [
  "from-blue-400 to-cyan-300",
  "from-purple-400 to-pink-300",
  "from-green-400 to-emerald-300",
  "from-orange-400 to-amber-300",
  "from-rose-400 to-red-300",
];

interface TripsTabProps {
  trips: TripItem[];
}

/**
 * Trips list tab with search filtering and empty state.
 */
export default function TripsTab({ trips }: TripsTabProps) {
  const [searchQuery, setSearchQuery] = useState("");

  // Filter trips by destination name
  const filteredTrips = useMemo(() => {
    if (!searchQuery.trim()) return trips;
    const q = searchQuery.trim().toLowerCase();
    return trips.filter((t) => t.destination.toLowerCase().includes(q));
  }, [trips, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Search bar */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
          />
        </svg>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="搜索目的地..."
          className="w-full bg-surface-container-high ghost-border rounded-xl py-2.5 pl-10 pr-4 text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {/* Trip cards */}
      {filteredTrips.length > 0 ? (
        <div className="space-y-3">
          {filteredTrips.map((trip, idx) => (
            <TripCard key={trip.id} trip={trip} colorIndex={idx} />
          ))}
        </div>
      ) : (
        <EmptyState hasSearch={searchQuery.trim().length > 0} />
      )}
    </div>
  );
}

/** Individual trip card */
function TripCard({
  trip,
  colorIndex,
}: {
  trip: TripItem;
  colorIndex: number;
}) {
  const status = statusMap[trip.status];
  const color = placeholderColors[colorIndex % placeholderColors.length];

  return (
    <Link
      href={`/itinerary/${trip.id}`}
      className="group flex gap-4 bg-surface-container-high ghost-border rounded-xl p-4 transition-all hover:shadow-lg hover:shadow-primary/10"
    >
      {/* Thumbnail placeholder */}
      <div
        className={`hidden h-20 w-28 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${color} sm:flex`}
      >
        <svg
          className="h-8 w-8 text-white/80"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"
          />
        </svg>
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="truncate text-base font-semibold text-on-surface group-hover:text-primary transition-colors">
            {trip.destination}
          </h3>
          <span
            className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${status.className}`}
          >
            {status.label}
          </span>
        </div>

        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-on-surface-variant">
          {/* Date */}
          <span className="inline-flex items-center gap-1">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
            </svg>
            {trip.startDate} ~ {trip.endDate}
          </span>
          {/* Travelers */}
          <span className="inline-flex items-center gap-1">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
            {trip.travelers} 人
          </span>
          {/* Budget */}
          <span className="inline-flex items-center gap-1">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {trip.currency} {trip.totalBudget.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Arrow indicator */}
      <div className="hidden items-center sm:flex">
        <svg
          className="h-5 w-5 text-on-surface-variant transition-transform group-hover:translate-x-1 group-hover:text-primary"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
      </div>
    </Link>
  );
}

/** Empty state when no trips */
function EmptyState({ hasSearch }: { hasSearch: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-outline-variant/30 bg-surface-container-low px-6 py-16">
      <svg
        className="mb-4 h-14 w-14 text-on-surface-variant/50"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth="1"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z"
        />
      </svg>
      <h3 className="mb-1 text-base font-semibold text-on-surface">
        {hasSearch ? "没有找到匹配的行程" : "还没有行程记录"}
      </h3>
      <p className="max-w-sm text-center text-sm text-on-surface-variant">
        {hasSearch
          ? "试试其他关键词搜索"
          : "开始一次 AI 对话，让我们为你规划完美旅程吧！"}
      </p>
      {!hasSearch && (
        <Link
          href="/chat"
          className="mt-4 inline-flex items-center gap-1.5 gradient-btn rounded-full px-4 py-2 text-sm font-medium transition-all"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          开始规划
        </Link>
      )}
    </div>
  );
}
