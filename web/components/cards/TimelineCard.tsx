"use client";

import { memo } from "react";
import { TimelineDayData, TimelineItem } from "@/lib/types";

interface TimelineCardProps {
  data: TimelineDayData;
}

// Map item type to icon and color
const typeStyles: Record<TimelineItem["type"], { color: string; bgColor: string; dotColor: string }> = {
  transport: { color: "text-primary", bgColor: "bg-primary/10", dotColor: "bg-primary" },
  attraction: { color: "text-secondary", bgColor: "bg-secondary/10", dotColor: "bg-secondary" },
  hotel: { color: "text-primary", bgColor: "bg-primary/10", dotColor: "bg-primary" },
  food: { color: "text-secondary", bgColor: "bg-secondary/10", dotColor: "bg-secondary" },
  activity: { color: "text-primary", bgColor: "bg-primary/10", dotColor: "bg-primary" },
};

/**
 * Timeline card for a single day's itinerary.
 */
export default memo(function TimelineCard({ data }: TimelineCardProps) {
  return (
    <div className="bg-surface-container-high ghost-border rounded-xl p-4">
      {/* Day header */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-bold text-white">
          D{data.day}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-on-surface">{data.title}</h3>
          <p className="text-xs text-on-surface-variant">{data.date}</p>
        </div>
      </div>

      {/* Timeline items */}
      <div className="relative ml-5 space-y-0">
        {/* Vertical line */}
        <div className="absolute left-0 top-0 h-full w-px bg-gradient-to-b from-primary to-transparent" />

        {data.items.map((item, index) => {
          const style = typeStyles[item.type] || typeStyles.activity;
          return (
            <div key={`${item.time}-${index}`} className="relative flex gap-3 pb-4 last:pb-0 animate-fade-in" style={{ animationDelay: `${index * 0.08}s` }}>
              {/* Dot on timeline */}
              <div className={`relative z-10 mt-1 flex h-5 w-5 -translate-x-[10px] items-center justify-center rounded-full ${style.bgColor}`}>
                <div className={`h-2 w-2 rounded-full ${style.dotColor}`} />
              </div>

              {/* Content */}
              <div className="-mt-0.5 flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-on-surface-variant">{item.time}</span>
                  {item.duration && (
                    <span className="shrink-0 bg-surface-container-highest text-on-surface-variant rounded-full px-2 py-0.5 text-xs">
                      {item.duration}
                    </span>
                  )}
                </div>
                <p className="text-sm font-medium text-on-surface break-words">{item.title}</p>
                <p className="text-xs text-on-surface-variant break-words">{item.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});
