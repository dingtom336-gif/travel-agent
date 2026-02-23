"use client";

import { memo } from "react";
import { POIData } from "@/lib/types";

interface POICardProps {
  data: POIData;
  onSelect?: () => void;
}

// Map POI type to Chinese display name
const typeLabels: Record<string, string> = {
  scenic: "景点",
  restaurant: "餐厅",
  shopping: "购物",
  activity: "活动",
  museum: "博物馆",
  park: "公园",
};

/**
 * Point of Interest card component.
 */
export default memo(function POICard({ data, onSelect }: POICardProps) {
  const handleClick = () => {
    const query = encodeURIComponent(data.name);
    window.open(`https://www.google.com/maps/search/${query}`, "_blank", "noopener");
    onSelect?.();
  };

  return (
    <button
      type="button"
      className="group w-full cursor-pointer overflow-hidden rounded-xl border border-border bg-card text-left transition-all duration-200 hover:border-primary/30 hover:shadow-md hover:scale-[1.01]"
      onClick={handleClick}
    >
      {/* Image with gradient overlay */}
      <div className="relative h-28 w-full overflow-hidden bg-gradient-to-br from-green-100 to-emerald-100">
        {data.imageUrl ? (
          <img
            src={data.imageUrl}
            alt={data.name}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <svg className="h-10 w-10 text-green-300" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
            </svg>
          </div>
        )}
        {/* Bottom gradient overlay */}
        <div className="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-black/20 to-transparent" />
        {/* Type badge */}
        <div className="absolute left-2 top-2 rounded-lg bg-white/90 px-2 py-0.5 text-xs font-medium text-green-600 backdrop-blur-sm">
          {typeLabels[data.type] || data.type}
        </div>
      </div>

      {/* Content */}
      <div className="p-2.5 sm:p-3">
        <div className="mb-1 flex items-start justify-between gap-1">
          <h3 className="truncate text-sm font-semibold text-card-foreground">{data.name}</h3>
          <div className="flex shrink-0 items-center gap-0.5">
            <svg className="h-3.5 w-3.5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            <span className="text-xs font-medium text-card-foreground">{data.rating}</span>
          </div>
        </div>

        <p className="mb-2 line-clamp-2 text-xs text-muted-foreground">
          {data.description}
        </p>

        <div className="flex items-center justify-between gap-1 text-xs text-muted-foreground">
          {data.openingHours && (
            <span className="flex min-w-0 items-center gap-1 truncate">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {data.openingHours}
            </span>
          )}
          {data.ticketPrice !== undefined && (
            <span className="font-medium text-primary">
              {data.ticketPrice === 0 ? "免费" : `${data.currency || "¥"}${data.ticketPrice}`}
            </span>
          )}
        </div>
      </div>
    </button>
  );
});
