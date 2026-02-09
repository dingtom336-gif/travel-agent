"use client";

import { memo } from "react";
import { useTravelPlan } from "@/lib/travel-context";

// Safe getter for data that may use camelCase or snake_case
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function get(obj: any, ...keys: string[]): unknown {
  for (const k of keys) {
    if (obj[k] !== undefined) return obj[k];
  }
  return undefined;
}

/**
 * Real-time itinerary preview sidebar.
 * Consumes TravelPlanContext and renders data as agents complete.
 */
export default memo(function ItinerarySidebar() {
  const { state, hasData } = useTravelPlan();

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">行程预览</h2>
        {hasData ? (
          <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-600">
            实时更新
          </span>
        ) : (
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
            等待中
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {!hasData && <EmptyState />}

        {hasData && (
          <div className="space-y-4">
            {/* Flights */}
            {state.flights.length > 0 && (
              <Section title="航班" icon="✈️">
                {state.flights.map((f, i) => (
                  <MiniCard key={i}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-foreground">
                        {(get(f, "airline", "airline_en") as string) || "航班"}
                      </span>
                      <span className="text-xs font-bold text-primary">
                        ¥{(get(f, "price") as number) || 0}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                      <span>{(get(f, "departure", "departure_city") as string) || ""}</span>
                      <span>→</span>
                      <span>{(get(f, "arrival", "arrival_city") as string) || ""}</span>
                      <span className="ml-auto">
                        {(get(f, "duration", "duration_display") as string) || ""}
                      </span>
                    </div>
                  </MiniCard>
                ))}
              </Section>
            )}

            {/* Hotels */}
            {state.hotels.length > 0 && (
              <Section title="酒店" icon="🏨">
                {state.hotels.map((h, i) => (
                  <MiniCard key={i}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-foreground">
                        {(get(h, "name") as string) || ""}
                      </span>
                      <span className="text-xs text-amber-500">
                        {"★".repeat(Math.min((get(h, "stars", "rating") as number) || 0, 5))}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {(get(h, "location") as string) || ""}
                      <span className="ml-2 font-medium text-primary">
                        ¥{(get(h, "pricePerNight", "price_per_night") as number) || 0}/晚
                      </span>
                    </div>
                  </MiniCard>
                ))}
              </Section>
            )}

            {/* Weather */}
            {state.weather.length > 0 && (
              <Section title="天气" icon="🌤️">
                <div className="grid grid-cols-3 gap-1.5">
                  {state.weather.map((w, i) => {
                    const temp = w.temperature as { high: number; low: number } | undefined;
                    const hi = temp?.high ?? (get(w, "high_temp") as number) ?? "";
                    const lo = temp?.low ?? (get(w, "low_temp") as number) ?? "";
                    return (
                      <div key={i} className="rounded-lg bg-muted/50 p-2 text-center">
                        <div className="text-xs text-muted-foreground">
                          {(get(w, "date") as string) || `Day ${i + 1}`}
                        </div>
                        <div className="text-sm font-medium">
                          {(get(w, "condition") as string) || ""}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {lo}°~{hi}°
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Section>
            )}

            {/* POIs */}
            {state.pois.length > 0 && (
              <Section title="推荐景点" icon="📍">
                {state.pois.map((p, i) => {
                  const poiName = (get(p, "name") as string) || "";
                  return (
                    <MiniCard
                      key={i}
                      onClick={() => {
                        if (poiName) {
                          window.open(
                            `https://www.google.com/maps/search/${encodeURIComponent(poiName)}`,
                            "_blank",
                            "noopener",
                          );
                        }
                      }}
                      className="cursor-pointer hover:bg-muted/80 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-foreground">
                          {poiName}
                        </span>
                        <span className="text-xs text-amber-500">
                          ★ {(get(p, "rating") as number) || 0}
                        </span>
                      </div>
                      <div className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
                        {(get(p, "description", "desc") as string) || (get(p, "type", "category") as string) || ""}
                      </div>
                    </MiniCard>
                  );
                })}
              </Section>
            )}

            {/* Itinerary timeline */}
            {state.itinerary.length > 0 && (
              <Section title="日程安排" icon="📋">
                {state.itinerary.map((day, i) => {
                  const dayNum = (get(day, "day") as number) || i + 1;
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  const rawItems = (day.items || (day as any).schedule || []) as unknown;
                  const items = (rawItems as Array<Record<string, unknown>>) || [];
                  return (
                    <div key={i} className="mb-2">
                      <div className="mb-1 flex items-center gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
                          {dayNum}
                        </span>
                        <span className="text-xs font-medium text-foreground">
                          Day {dayNum}
                        </span>
                      </div>
                      <div className="ml-6 space-y-1">
                        {items.slice(0, 4).map((item, j) => (
                          <div
                            key={j}
                            className="flex items-center gap-1.5 text-xs text-muted-foreground"
                          >
                            <div className="h-1 w-1 rounded-full bg-primary/50" />
                            <span>
                              {(get(item, "time", "start_time") as string) || ""}
                            </span>
                            <span className="font-medium text-foreground">
                              {(get(item, "title", "poi_name") as string) || ""}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </Section>
            )}

            {/* Budget */}
            {state.budget && (
              <Section title="预算概览" icon="💰">
                <MiniCard>
                  <div className="text-xs text-muted-foreground">
                    总预算：
                    <span className="font-bold text-foreground">
                      ¥{(get(state.budget, "totalBudget", "total_budget") as number) || 0}
                    </span>
                  </div>
                </MiniCard>
              </Section>
            )}
          </div>
        )}
      </div>
    </div>
  );
});

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
        <svg
          className="h-6 w-6 text-muted-foreground"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"
          />
        </svg>
      </div>
      <p className="mb-1 text-sm font-medium text-foreground">暂无行程</p>
      <p className="text-xs text-muted-foreground">
        开始对话后，行程会自动在这里生成
      </p>
    </div>
  );
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5">
        <span className="text-sm">{icon}</span>
        <h3 className="text-xs font-semibold text-foreground">{title}</h3>
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function MiniCard({
  children,
  onClick,
  className,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  const base = "rounded-lg border border-border/60 bg-card p-2.5 transition-colors hover:bg-muted/30";
  return (
    <div
      className={className ? `${base} ${className}` : base}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter") onClick(); } : undefined}
    >
      {children}
    </div>
  );
}
