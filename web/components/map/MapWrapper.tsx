"use client";

import dynamic from "next/dynamic";
import { TimelineDayData } from "@/lib/types";

// Dynamic import with SSR disabled - Leaflet requires browser APIs
const ItineraryMap = dynamic(() => import("./ItineraryMap"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center rounded-xl border border-border bg-muted/30" style={{ height: 480 }}>
      <div className="flex flex-col items-center gap-2">
        <div className="h-8 w-8 animate-spin-slow rounded-full border-2 border-primary border-t-transparent" />
        <span className="text-sm text-muted-foreground">Loading map...</span>
      </div>
    </div>
  ),
});

interface MapWrapperProps {
  days: TimelineDayData[];
  selectedDay?: number | null;
}

export default function MapWrapper({ days, selectedDay }: MapWrapperProps) {
  return <ItineraryMap days={days} selectedDay={selectedDay} />;
}
