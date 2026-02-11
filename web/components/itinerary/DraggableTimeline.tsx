"use client";

import { useCallback } from "react";
import {
  DragDropContext,
  Droppable,
  Draggable,
  type DropResult,
} from "@hello-pangea/dnd";
import type { TimelineDayData, TimelineItem } from "@/lib/types";

// Item type styles
const typeStyles: Record<
  TimelineItem["type"],
  { color: string; bgColor: string; dotColor: string }
> = {
  transport: { color: "text-sky-500", bgColor: "bg-sky-100", dotColor: "bg-sky-500" },
  attraction: { color: "text-green-500", bgColor: "bg-green-100", dotColor: "bg-green-500" },
  hotel: { color: "text-purple-500", bgColor: "bg-purple-100", dotColor: "bg-purple-500" },
  food: { color: "text-orange-500", bgColor: "bg-orange-100", dotColor: "bg-orange-500" },
  activity: { color: "text-pink-500", bgColor: "bg-pink-100", dotColor: "bg-pink-500" },
};

interface DraggableTimelineProps {
  days: TimelineDayData[];
  expandedDays: Set<number>;
  onToggleDay: (day: number) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onReorder: (updatedDays: TimelineDayData[]) => void;
}

export default function DraggableTimeline({
  days,
  expandedDays,
  onToggleDay,
  onExpandAll,
  onCollapseAll,
  onReorder,
}: DraggableTimelineProps) {
  const handleDragEnd = useCallback(
    (result: DropResult) => {
      const { source, destination } = result;
      if (!destination) return;
      if (
        source.droppableId === destination.droppableId &&
        source.index === destination.index
      ) {
        return;
      }

      const srcDayNum = parseInt(source.droppableId.replace("day-", ""), 10);
      const dstDayNum = parseInt(destination.droppableId.replace("day-", ""), 10);

      const updated = days.map((d) => ({ ...d, items: [...d.items] }));
      const srcDay = updated.find((d) => d.day === srcDayNum);
      const dstDay = updated.find((d) => d.day === dstDayNum);
      if (!srcDay || !dstDay) return;

      const [moved] = srcDay.items.splice(source.index, 1);
      dstDay.items.splice(destination.index, 0, moved);

      onReorder(updated);
    },
    [days, onReorder]
  );

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

      <DragDropContext onDragEnd={handleDragEnd}>
        {days.map((day) => {
          const isExpanded = expandedDays.has(day.day);
          return (
            <div key={day.day} className="animate-fade-in">
              {/* Day header */}
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

              {/* Droppable items area */}
              {isExpanded && (
                <Droppable droppableId={`day-${day.day}`}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={`mt-2 rounded-xl border p-4 transition-colors ${
                        snapshot.isDraggingOver
                          ? "border-primary/50 bg-primary/5"
                          : "border-border bg-card"
                      }`}
                    >
                      {/* Day label */}
                      <div className="mb-4 flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-bold text-white">
                          D{day.day}
                        </div>
                        <div>
                          <h3 className="text-sm font-semibold text-card-foreground">{day.title}</h3>
                          <p className="text-xs text-muted-foreground">{day.date}</p>
                        </div>
                      </div>

                      <div className="relative ml-5 space-y-0">
                        <div className="absolute left-0 top-0 h-full w-px bg-border" />
                        {day.items.map((item, index) => (
                          <Draggable
                            key={`${day.day}-${index}`}
                            draggableId={`${day.day}-${index}`}
                            index={index}
                          >
                            {(dragProvided, dragSnapshot) => {
                              const style = typeStyles[item.type] || typeStyles.activity;
                              return (
                                <div
                                  ref={dragProvided.innerRef}
                                  {...dragProvided.draggableProps}
                                  {...dragProvided.dragHandleProps}
                                  className={`relative flex gap-3 pb-4 last:pb-0 rounded-lg transition-shadow ${
                                    dragSnapshot.isDragging
                                      ? "shadow-lg bg-card z-50 ring-2 ring-primary/30"
                                      : ""
                                  }`}
                                >
                                  <div className={`relative z-10 mt-1 flex h-5 w-5 -translate-x-[10px] items-center justify-center rounded-full ${style.bgColor}`}>
                                    <div className={`h-2 w-2 rounded-full ${style.dotColor}`} />
                                  </div>
                                  <div className="-mt-0.5 flex-1">
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs font-medium text-muted-foreground">
                                        {item.time}
                                      </span>
                                      {item.duration && (
                                        <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                                          {item.duration}
                                        </span>
                                      )}
                                      {/* Drag handle indicator */}
                                      <svg
                                        className="ml-auto h-4 w-4 text-muted-foreground/40"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        strokeWidth="1.5"
                                        stroke="currentColor"
                                      >
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
                                      </svg>
                                    </div>
                                    <p className="text-sm font-medium text-card-foreground">
                                      {item.title}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                      {item.description}
                                    </p>
                                  </div>
                                </div>
                              );
                            }}
                          </Draggable>
                        ))}
                        {provided.placeholder}
                      </div>
                    </div>
                  )}
                </Droppable>
              )}
            </div>
          );
        })}
      </DragDropContext>
    </div>
  );
}
