"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { TimelineDayData, GeoLocation } from "@/lib/types";

// Fix default marker icon issue with Leaflet + webpack
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Day color palette for markers and routes
const DAY_COLORS = [
  "#2563eb", // blue
  "#16a34a", // green
  "#ea580c", // orange
  "#9333ea", // purple
  "#e11d48", // rose
  "#0891b2", // cyan
  "#ca8a04", // yellow
  "#6366f1", // indigo
];

// Icon type mapping
const TYPE_EMOJI: Record<string, string> = {
  transport: "🚄",
  attraction: "📍",
  hotel: "🏨",
  food: "🍜",
  activity: "🎯",
};

interface ItineraryMapProps {
  days: TimelineDayData[];
  selectedDay?: number | null;
}

interface MapMarker {
  position: [number, number];
  title: string;
  description: string;
  type: string;
  time: string;
  day: number;
  dayTitle: string;
  color: string;
  duration?: string;
}

// Create a colored circle marker icon
function createDayIcon(day: number, color: string, type: string): L.DivIcon {
  const emoji = TYPE_EMOJI[type] || "📍";
  return L.divIcon({
    className: "custom-map-marker",
    html: `
      <div style="
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: ${color};
        color: white;
        font-size: 14px;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        border: 2px solid white;
        cursor: pointer;
      ">${emoji}</div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
}

// Component to auto-fit map bounds
function FitBounds({ markers }: { markers: MapMarker[] }) {
  const map = useMap();

  useEffect(() => {
    if (markers.length === 0) return;
    const bounds = L.latLngBounds(markers.map((m) => m.position));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
  }, [map, markers]);

  return null;
}

export default function ItineraryMap({ days, selectedDay }: ItineraryMapProps) {
  const [activeDay, setActiveDay] = useState<number | null>(selectedDay ?? null);

  // Build markers from itinerary days
  const allMarkers = useMemo<MapMarker[]>(() => {
    const markers: MapMarker[] = [];
    days.forEach((day) => {
      const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
      day.items.forEach((item) => {
        if (item.location) {
          markers.push({
            position: [item.location.lat, item.location.lng],
            title: item.title,
            description: item.description,
            type: item.type,
            time: item.time,
            day: day.day,
            dayTitle: day.title,
            color,
            duration: item.duration,
          });
        }
      });
    });
    return markers;
  }, [days]);

  // Filter markers by selected day
  const visibleMarkers = useMemo(() => {
    if (activeDay === null) return allMarkers;
    return allMarkers.filter((m) => m.day === activeDay);
  }, [allMarkers, activeDay]);

  // Build route polylines per day
  const polylines = useMemo(() => {
    const lines: { positions: [number, number][]; color: string; day: number }[] = [];
    days.forEach((day) => {
      if (activeDay !== null && day.day !== activeDay) return;
      const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
      const positions: [number, number][] = [];
      day.items.forEach((item) => {
        if (item.location) {
          positions.push([item.location.lat, item.location.lng]);
        }
      });
      if (positions.length >= 2) {
        lines.push({ positions, color, day: day.day });
      }
    });
    return lines;
  }, [days, activeDay]);

  // Default center (Tokyo area)
  const defaultCenter: [number, number] = useMemo(() => {
    if (allMarkers.length > 0) {
      const avgLat = allMarkers.reduce((s, m) => s + m.position[0], 0) / allMarkers.length;
      const avgLng = allMarkers.reduce((s, m) => s + m.position[1], 0) / allMarkers.length;
      return [avgLat, avgLng];
    }
    return [35.6762, 139.6503]; // Tokyo
  }, [allMarkers]);

  return (
    <div className="space-y-3">
      {/* Day filter chips */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveDay(null)}
          className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
            activeDay === null
              ? "bg-primary text-white"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          全部
        </button>
        {days.map((day) => {
          const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
          const isActive = activeDay === day.day;
          return (
            <button
              key={day.day}
              onClick={() => setActiveDay(isActive ? null : day.day)}
              className="rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
              style={{
                backgroundColor: isActive ? color : undefined,
                color: isActive ? "white" : color,
                border: `1.5px solid ${color}`,
              }}
            >
              D{day.day} {day.title}
            </button>
          );
        })}
      </div>

      {/* Map container */}
      <div className="overflow-hidden rounded-xl border border-border h-[280px] sm:h-[480px]">
        <MapContainer
          center={defaultCenter}
          zoom={11}
          scrollWheelZoom={true}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Auto-fit bounds */}
          <FitBounds markers={visibleMarkers} />

          {/* Route polylines */}
          {polylines.map((line) => (
            <Polyline
              key={`route-${line.day}`}
              positions={line.positions}
              pathOptions={{
                color: line.color,
                weight: 3,
                opacity: 0.7,
                dashArray: "8 4",
              }}
            />
          ))}

          {/* Markers */}
          {visibleMarkers.map((marker, i) => (
            <Marker
              key={`marker-${marker.day}-${i}`}
              position={marker.position}
              icon={createDayIcon(marker.day, marker.color, marker.type)}
            >
              <Popup>
                <div style={{ minWidth: 180, fontFamily: "system-ui, sans-serif" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 22,
                        height: 22,
                        borderRadius: "50%",
                        backgroundColor: marker.color,
                        color: "white",
                        fontSize: 11,
                        fontWeight: 700,
                      }}
                    >
                      {marker.day}
                    </span>
                    <span style={{ fontSize: 12, color: "#64748b" }}>
                      {marker.time}
                      {marker.duration && ` (${marker.duration})`}
                    </span>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>
                    {TYPE_EMOJI[marker.type]} {marker.title}
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b", lineHeight: 1.4 }}>
                    {marker.description}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span className="font-medium">图例：</span>
        {Object.entries(TYPE_EMOJI).map(([type, emoji]) => (
          <span key={type} className="inline-flex items-center gap-1">
            {emoji} {type === "transport" ? "交通" : type === "attraction" ? "景点" : type === "hotel" ? "住宿" : type === "food" ? "美食" : "活动"}
          </span>
        ))}
      </div>
    </div>
  );
}
