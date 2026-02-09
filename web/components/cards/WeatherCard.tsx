"use client";

import { memo } from "react";
import { WeatherData } from "@/lib/types";

interface WeatherCardProps {
  data: WeatherData;
}

const conditionLabels: Record<string, string> = {
  sunny: "晴",
  cloudy: "多云",
  rainy: "雨",
  snowy: "雪",
  overcast: "阴",
};

// Map weather condition to icon and color
const weatherIcons: Record<string, { icon: string; color: string; bg: string }> = {
  sunny: { icon: "sun", color: "text-yellow-500", bg: "from-yellow-50 to-orange-50 dark:from-yellow-950/30 dark:to-orange-950/20" },
  cloudy: { icon: "cloud", color: "text-gray-400", bg: "from-gray-50 to-slate-50 dark:from-gray-900/30 dark:to-slate-900/20" },
  rainy: { icon: "rain", color: "text-blue-400", bg: "from-blue-50 to-cyan-50 dark:from-blue-950/30 dark:to-cyan-950/20" },
  snowy: { icon: "snow", color: "text-blue-200", bg: "from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/20" },
  overcast: { icon: "cloud", color: "text-gray-500", bg: "from-gray-100 to-slate-100 dark:from-gray-900/30 dark:to-slate-800/20" },
};

/**
 * Weather card component showing city weather info.
 */
export default memo(function WeatherCard({ data }: WeatherCardProps) {
  const weather = weatherIcons[data.condition] || weatherIcons.sunny;

  return (
    <div className={`rounded-xl border border-border bg-gradient-to-br ${weather.bg} p-4`}>
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-card-foreground">{data.city}</h3>
          <p className="text-xs text-muted-foreground">{data.date}</p>
        </div>
        {/* Weather icon */}
        <div className={`${weather.color}`}>
          <WeatherIcon type={weather.icon} />
        </div>
      </div>

      {/* Temperature */}
      <div className="mb-3 flex items-baseline gap-1">
        <span className="text-2xl font-bold text-card-foreground">
          {data.temperature.high}&deg;
        </span>
        <span className="text-sm text-muted-foreground">
          / {data.temperature.low}&deg;C
        </span>
      </div>

      {/* Details */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>湿度 {data.humidity}%</span>
        <span>{conditionLabels[data.condition] || "阴"}</span>
      </div>

      {/* Suggestion */}
      {data.suggestion && (
        <div className="mt-2 rounded-lg bg-card/60 p-2 text-xs text-muted-foreground">
          {data.suggestion}
        </div>
      )}
    </div>
  );
});

function WeatherIcon({ type }: { type: string }) {
  if (type === "sun") {
    return (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
      </svg>
    );
  }
  if (type === "cloud") {
    return (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" />
      </svg>
    );
  }
  if (type === "rain") {
    return (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19.5v2m3-2v2m3-2v2" />
      </svg>
    );
  }
  // Default snow
  return (
    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19l.5 1m2.5-1l.5 1m2.5-1l.5 1" />
    </svg>
  );
}
