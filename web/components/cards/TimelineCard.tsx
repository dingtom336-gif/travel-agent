"use client";

import { memo } from "react";
import { TimelineDayData, TimelineItem } from "@/lib/types";

interface TimelineCardProps {
  data: TimelineDayData;
}

// Map item type to icon and color
const typeStyles: Record<TimelineItem["type"], { color: string; bgColor: string; dotColor: string }> = {
  transport: { color: "text-sky-500", bgColor: "bg-sky-100", dotColor: "bg-sky-500" },
  attraction: { color: "text-green-500", bgColor: "bg-green-100", dotColor: "bg-green-500" },
  hotel: { color: "text-purple-500", bgColor: "bg-purple-100", dotColor: "bg-purple-500" },
  food: { color: "text-orange-500", bgColor: "bg-orange-100", dotColor: "bg-orange-500" },
  activity: { color: "text-pink-500", bgColor: "bg-pink-100", dotColor: "bg-pink-500" },
};

/**
 * Timeline card for a single day's itinerary.
 */
export default memo(function TimelineCard({ data }: TimelineCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      {/* Day header */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-bold text-white">
          D{data.day}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-card-foreground">{data.title}</h3>
          <p className="text-xs text-muted-foreground">{data.date}</p>
        </div>
      </div>

      {/* Timeline items */}
      <div className="relative ml-5 space-y-0">
        {/* Vertical line */}
        <div className="absolute left-0 top-0 h-full w-px bg-border" />

        {data.items.map((item, index) => {
          const style = typeStyles[item.type] || typeStyles.activity;
          return (
            <div key={`${item.time}-${index}`} className="relative flex gap-3 pb-4 last:pb-0 animate-fade-in" style={{ animationDelay: `${index * 0.08}s` }}>
              {/* Dot on timeline */}
              <div className={`relative z-10 mt-1 flex h-5 w-5 -translate-x-[10px] items-center justify-center rounded-full ${style.bgColor}`}>
                <div className={`h-2 w-2 rounded-full ${style.dotColor}`} />
              </div>

              {/* Content */}
              <div className="-mt-0.5 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-muted-foreground">{item.time}</span>
                  {item.duration && (
                    <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                      {item.duration}
                    </span>
                  )}
                </div>
                <p className="text-sm font-medium text-card-foreground">{item.title}</p>
                <p className="text-xs text-muted-foreground">{item.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});
