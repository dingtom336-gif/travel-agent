"use client";

import { HotelData } from "@/lib/types";

interface HotelCardProps {
  data: HotelData;
  onSelect?: () => void;
}

/**
 * Hotel card component displaying name, rating, location, price, and amenities.
 */
export default function HotelCard({ data, onSelect }: HotelCardProps) {
  return (
    <button
      type="button"
      className="group w-full cursor-pointer overflow-hidden rounded-xl border border-border bg-card text-left transition-all duration-200 hover:border-primary/30 hover:shadow-md hover:scale-[1.01]"
      onClick={onSelect}
    >
      {/* Image with gradient overlay */}
      <div className="relative h-32 w-full overflow-hidden bg-gradient-to-br from-purple-100 to-blue-100">
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
            <svg className="h-10 w-10 text-purple-300" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 0h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008z" />
            </svg>
          </div>
        )}
        {/* Bottom gradient overlay for text readability */}
        <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/20 to-transparent" />
        {/* Star badge */}
        <div className="absolute right-2 top-2 rounded-lg bg-white/90 px-2 py-0.5 text-xs font-medium text-yellow-600 backdrop-blur-sm" aria-label={`${data.stars}星级`}>
          {"★".repeat(data.stars)} {data.stars}星
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="mb-2 flex items-start justify-between">
          <div>
            <h3 className="text-sm font-semibold text-card-foreground">{data.name}</h3>
            <p className="text-xs text-muted-foreground">{data.location}</p>
          </div>
          <div className="flex items-center gap-1 rounded bg-green-50 px-1.5 py-0.5">
            <span className="text-xs font-bold text-green-600">{data.rating}</span>
            <svg className="h-3 w-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          </div>
        </div>

        {/* Amenities */}
        <div className="mb-3 flex flex-wrap gap-1">
          {data.amenities.slice(0, 4).map((amenity) => (
            <span
              key={amenity}
              className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
            >
              {amenity}
            </span>
          ))}
        </div>

        {/* Price */}
        <div className="flex items-baseline gap-1">
          <span className="text-lg font-bold text-primary">
            {data.currency}{data.pricePerNight}
          </span>
          <span className="text-xs text-muted-foreground">/晚</span>
        </div>
      </div>
    </button>
  );
}
