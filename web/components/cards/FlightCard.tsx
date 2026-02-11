"use client";

import { memo } from "react";
import { FlightData } from "@/lib/types";

interface FlightCardProps {
  data: FlightData;
  onSelect?: () => void;
}

/**
 * Flight card component displaying airline, route, time, and price.
 */
export default memo(function FlightCard({ data, onSelect }: FlightCardProps) {
  return (
    <button
      type="button"
      className="group w-full cursor-pointer rounded-xl border border-border bg-card p-4 text-left transition-all duration-200 hover:border-primary/30 hover:shadow-md hover:scale-[1.01]"
      onClick={onSelect}
    >
      {/* Header: airline + flight number */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-100 text-sky-600 dark:bg-sky-900/30 dark:text-sky-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-card-foreground">{data.airline}</p>
            <p className="text-xs text-muted-foreground">{data.flightNo}</p>
          </div>
        </div>
        <span className="text-base font-bold text-primary sm:text-lg">
          {data.currency}{data.price}
        </span>
      </div>

      {/* Route visualization */}
      <div className="flex items-center justify-between">
        {/* Departure */}
        <div className="text-center">
          <p className="text-base font-bold text-card-foreground sm:text-lg">{data.departTime}</p>
          <p className="text-xs text-muted-foreground">{data.departure}</p>
        </div>

        {/* Duration + line */}
        <div className="flex flex-1 flex-col items-center px-3">
          <p className="mb-1 text-xs text-muted-foreground">{data.duration}</p>
          <div className="relative w-full">
            <div className="h-px w-full bg-border" />
            <div className="absolute left-0 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-primary" />
            <div className="absolute right-0 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-primary" />
            <svg
              className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 text-muted-foreground"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">直飞</p>
        </div>

        {/* Arrival */}
        <div className="text-center">
          <p className="text-base font-bold text-card-foreground sm:text-lg">{data.arriveTime}</p>
          <p className="text-xs text-muted-foreground">{data.arrival}</p>
        </div>
      </div>
    </button>
  );
});
