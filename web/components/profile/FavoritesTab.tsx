"use client";

import { FavoriteItem } from "@/lib/mock-profile";

// Type label & style map
const typeMap: Record<
  FavoriteItem["type"],
  { label: string; className: string }
> = {
  attraction: {
    label: "景点",
    className: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  },
  hotel: {
    label: "酒店",
    className: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  },
  guide: {
    label: "攻略",
    className: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  },
};

// Placeholder icon colors (deterministic by index)
const placeholderGradients = [
  "from-sky-400 to-blue-500",
  "from-violet-400 to-purple-500",
  "from-emerald-400 to-green-500",
  "from-amber-400 to-orange-500",
  "from-rose-400 to-pink-500",
  "from-cyan-400 to-teal-500",
];

interface FavoritesTabProps {
  favorites: FavoriteItem[];
}

/**
 * Favorites grid tab with type badges and ratings.
 */
export default function FavoritesTab({ favorites }: FavoritesTabProps) {
  if (favorites.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {favorites.map((item, idx) => (
        <FavoriteCard key={item.id} item={item} colorIndex={idx} />
      ))}
    </div>
  );
}

/** Individual favorite card */
function FavoriteCard({
  item,
  colorIndex,
}: {
  item: FavoriteItem;
  colorIndex: number;
}) {
  const type = typeMap[item.type];
  const gradient = placeholderGradients[colorIndex % placeholderGradients.length];

  return (
    <div className="group overflow-hidden rounded-xl border border-border bg-card transition-all hover:border-primary/30 hover:shadow-md">
      {/* Image placeholder */}
      <div
        className={`flex h-36 items-center justify-center bg-gradient-to-br ${gradient}`}
      >
        <TypeIcon type={item.type} />
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-card-foreground group-hover:text-primary transition-colors">
            {item.name}
          </h3>
          <span
            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${type.className}`}
          >
            {type.label}
          </span>
        </div>

        <p className="mt-1 text-xs text-muted-foreground">{item.location}</p>

        {/* Rating */}
        <div className="mt-2 flex items-center gap-1">
          <svg
            className="h-4 w-4 text-amber-400"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
          <span className="text-sm font-medium text-card-foreground">
            {item.rating}
          </span>
        </div>
      </div>
    </div>
  );
}

/** Icon per favorite type */
function TypeIcon({ type }: { type: FavoriteItem["type"] }) {
  if (type === "attraction") {
    return (
      <svg className="h-12 w-12 text-white/80" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
      </svg>
    );
  }
  if (type === "hotel") {
    return (
      <svg className="h-12 w-12 text-white/80" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21" />
      </svg>
    );
  }
  // guide
  return (
    <svg className="h-12 w-12 text-white/80" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
    </svg>
  );
}

/** Empty state when no favorites */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-border bg-muted/30 px-6 py-16">
      <svg
        className="mb-4 h-14 w-14 text-muted-foreground/50"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth="1"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z"
        />
      </svg>
      <h3 className="mb-1 text-base font-semibold text-card-foreground">
        还没有收藏内容
      </h3>
      <p className="max-w-sm text-center text-sm text-muted-foreground">
        浏览行程时可以收藏喜欢的景点、酒店和攻略
      </p>
    </div>
  );
}
