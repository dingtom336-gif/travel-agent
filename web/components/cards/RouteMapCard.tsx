"use client";

import { memo, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { GeoLocation } from "@/lib/types";

// Dynamically import Leaflet components to avoid SSR issues
const MapContainer = dynamic(
  () => import("react-leaflet").then((mod) => mod.MapContainer),
  { ssr: false },
);
const TileLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.TileLayer),
  { ssr: false },
);
const Marker = dynamic(
  () => import("react-leaflet").then((mod) => mod.Marker),
  { ssr: false },
);
const Polyline = dynamic(
  () => import("react-leaflet").then((mod) => mod.Polyline),
  { ssr: false },
);
const Tooltip = dynamic(
  () => import("react-leaflet").then((mod) => mod.Tooltip),
  { ssr: false },
);

export interface RouteMapData {
  points: GeoLocation[];
  title?: string;
}

interface RouteMapCardProps {
  data: RouteMapData;
}

/**
 * Route map card showing travel route as polyline with markers.
 * Uses Leaflet via react-leaflet (already installed).
 */
export default memo(function RouteMapCard({ data }: RouteMapCardProps) {
  const { points, title } = data;

  if (!points || points.length === 0) return null;

  // Calculate map center and bounds
  const center: [number, number] = [
    points.reduce((sum, p) => sum + p.lat, 0) / points.length,
    points.reduce((sum, p) => sum + p.lng, 0) / points.length,
  ];

  const positions: [number, number][] = points.map((p) => [p.lat, p.lng]);

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      {title && (
        <div className="border-b border-border/50 px-4 py-2">
          <h4 className="text-sm font-semibold text-card-foreground">{title}</h4>
        </div>
      )}
      <div className="h-[200px] w-full">
        <MapContainer
          center={center}
          zoom={6}
          scrollWheelZoom={false}
          style={{ height: "100%", width: "100%" }}
          attributionControl={false}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Polyline
            positions={positions}
            pathOptions={{ color: "#2563eb", weight: 3, dashArray: "8 4" }}
          />
          {points.map((point, idx) => (
            <Marker key={idx} position={[point.lat, point.lng]}>
              {point.label && (
                <Tooltip permanent direction="top" offset={[0, -10]}>
                  <span className="text-xs font-medium">{point.label}</span>
                </Tooltip>
              )}
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
});
