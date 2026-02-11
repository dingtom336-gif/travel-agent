"use client";

import { useState, useEffect } from "react";
import TripsTab from "@/components/profile/TripsTab";
import PreferencesTab from "@/components/profile/PreferencesTab";
import FavoritesTab from "@/components/profile/FavoritesTab";
import {
  mockUser,
  mockTrips,
  mockFavorites,
  mockPreferences,
  type UserProfile,
  type TripItem,
  type UserPreferences,
} from "@/lib/mock-profile";
import { getProfile, getItineraries } from "@/lib/api-client";

type ProfileTab = "trips" | "preferences" | "favorites";

/**
 * Profile page with user info header and tab-based content.
 * Route: /profile
 */
export default function ProfilePage() {
  const [activeTab, setActiveTab] = useState<ProfileTab>("trips");
  const [user, setUser] = useState<UserProfile>(mockUser);
  const [trips, setTrips] = useState<TripItem[]>(mockTrips);
  const [preferences, setPreferences] = useState<UserPreferences>(mockPreferences);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [profileRes, itinRes] = await Promise.all([
          getProfile(),
          getItineraries(),
        ]);
        if (cancelled) return;
        if (profileRes && typeof profileRes === "object") {
          const p = profileRes as Record<string, unknown>;
          if (p.name) {
            setUser((prev) => ({
              ...prev,
              name: (p.name as string) || prev.name,
              email: (p.email as string) || prev.email,
              memberLevel: (p.member_level as string) || prev.memberLevel,
              totalTrips: (p.total_trips as number) ?? prev.totalTrips,
              totalDestinations: (p.total_destinations as number) ?? prev.totalDestinations,
            }));
          }
          if (p.travel_style || p.budget_preference) {
            setPreferences((prev) => ({
              ...prev,
              travelStyles: (p.travel_style as UserPreferences["travelStyles"]) || prev.travelStyles,
              budgetLevel: (p.budget_preference as UserPreferences["budgetLevel"]) || prev.budgetLevel,
              transportPref: (p.transport_pref as UserPreferences["transportPref"]) || prev.transportPref,
            }));
          }
        }
        if (itinRes && typeof itinRes === "object" && !Array.isArray(itinRes)) {
          const obj = itinRes as Record<string, unknown>;
          if ("itineraries" in obj) {
            const items = obj.itineraries as TripItem[];
            if (items && items.length > 0) {
              setTrips(items);
            }
          }
        }
      } catch {
        // Fall back to mock data (already set as defaults)
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // Tab definitions
  const tabs: { key: ProfileTab; label: string; icon: React.ReactNode }[] = [
    {
      key: "trips",
      label: "我的行程",
      icon: (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
        </svg>
      ),
    },
    {
      key: "preferences",
      label: "偏好设置",
      icon: (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    },
    {
      key: "favorites",
      label: "收藏夹",
      icon: (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-background">
      {/* User profile header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
            {/* Avatar */}
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent text-2xl font-bold text-white">
              {user.name.charAt(0)}
            </div>

            {/* User info */}
            <div className="flex-1 text-center sm:text-left">
              <div className="flex flex-col items-center gap-2 sm:flex-row">
                <h1 className="text-xl font-bold text-foreground sm:text-2xl">
                  {user.name}
                </h1>
                <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  {user.memberLevel}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {user.email}
              </p>

              {/* Stats row */}
              <div className="mt-3 flex flex-wrap justify-center gap-4 sm:justify-start">
                <StatBadge label="总行程" value={String(user.totalTrips)} />
                <StatBadge label="目的地" value={String(user.totalDestinations)} />
                <StatBadge
                  label="加入时间"
                  value={user.joinDate.slice(0, 7)}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Tab bar */}
        <div className="mx-auto max-w-4xl px-4 sm:px-6">
          <div className="flex gap-1 overflow-x-auto scrollbar-hide">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Tab content */}
      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : (
          <>
            {activeTab === "trips" && <TripsTab trips={trips} />}
            {activeTab === "preferences" && (
              <PreferencesTab initialPreferences={preferences} />
            )}
            {activeTab === "favorites" && (
              <FavoritesTab favorites={mockFavorites} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

/** Small stat badge for user header */
function StatBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="inline-flex items-center gap-1.5 rounded-lg bg-muted px-3 py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold text-card-foreground">
        {value}
      </span>
    </div>
  );
}
