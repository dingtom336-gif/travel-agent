"use client";

import { useState } from "react";
import {
  UserPreferences,
  TravelStyle,
  BudgetLevel,
  AccommodationType,
  TransportPref,
  DietaryRestriction,
  travelStyleLabels,
  budgetLevelLabels,
  accommodationLabels,
  transportPrefLabels,
  dietaryLabels,
} from "@/lib/mock-profile";

interface PreferencesTabProps {
  initialPreferences: UserPreferences;
}

/**
 * Preferences settings tab with toggle chips and save button.
 */
export default function PreferencesTab({ initialPreferences }: PreferencesTabProps) {
  const [prefs, setPrefs] = useState<UserPreferences>(initialPreferences);
  const [saved, setSaved] = useState(false);

  // Toggle a value in a multi-select array
  const toggleMulti = <T extends string>(
    key: keyof UserPreferences,
    value: T
  ) => {
    setSaved(false);
    setPrefs((prev) => {
      const arr = prev[key] as T[];
      const next = arr.includes(value)
        ? arr.filter((v) => v !== value)
        : [...arr, value];
      return { ...prev, [key]: next };
    });
  };

  // Set a single-select value
  const setSingle = <T extends string>(
    key: keyof UserPreferences,
    value: T
  ) => {
    setSaved(false);
    setPrefs((prev) => ({ ...prev, [key]: value }));
  };

  // Handle save – backend not yet available for MVP
  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-8">
      {/* Travel style (multi-select) */}
      <PreferenceSection
        title="出行风格"
        description="选择你偏好的旅行风格，可多选"
        icon={<MountainIcon />}
      >
        <div className="flex flex-wrap gap-2">
          {(Object.keys(travelStyleLabels) as TravelStyle[]).map((style) => {
            const selected = prefs.travelStyles.includes(style);
            return (
              <ChipButton
                key={style}
                label={travelStyleLabels[style].label}
                selected={selected}
                onClick={() => toggleMulti("travelStyles", style)}
              />
            );
          })}
        </div>
      </PreferenceSection>

      {/* Budget level (single-select) */}
      <PreferenceSection
        title="预算偏好"
        description="选择你通常的预算级别"
        icon={<WalletIcon />}
      >
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {(Object.keys(budgetLevelLabels) as BudgetLevel[]).map((level) => {
            const selected = prefs.budgetLevel === level;
            return (
              <RadioCard
                key={level}
                label={budgetLevelLabels[level].label}
                description={budgetLevelLabels[level].desc}
                selected={selected}
                onClick={() => setSingle("budgetLevel", level)}
              />
            );
          })}
        </div>
      </PreferenceSection>

      {/* Accommodation (multi-select) */}
      <PreferenceSection
        title="住宿偏好"
        description="偏好的住宿类型，可多选"
        icon={<BuildingIcon />}
      >
        <div className="flex flex-wrap gap-2">
          {(Object.keys(accommodationLabels) as AccommodationType[]).map((type) => {
            const selected = prefs.accommodations.includes(type);
            return (
              <ChipButton
                key={type}
                label={accommodationLabels[type].label}
                selected={selected}
                onClick={() => toggleMulti("accommodations", type)}
              />
            );
          })}
        </div>
      </PreferenceSection>

      {/* Transport preference (single-select) */}
      <PreferenceSection
        title="交通偏好"
        description="选择你的交通优先策略"
        icon={<PlaneIcon />}
      >
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {(Object.keys(transportPrefLabels) as TransportPref[]).map((pref) => {
            const selected = prefs.transportPref === pref;
            return (
              <RadioCard
                key={pref}
                label={transportPrefLabels[pref].label}
                description={transportPrefLabels[pref].desc}
                selected={selected}
                onClick={() => setSingle("transportPref", pref)}
              />
            );
          })}
        </div>
      </PreferenceSection>

      {/* Dietary restrictions (multi-select) */}
      <PreferenceSection
        title="饮食限制"
        description="有特殊饮食需求请选择，可多选"
        icon={<UtensilsIcon />}
      >
        <div className="flex flex-wrap gap-2">
          {(Object.keys(dietaryLabels) as DietaryRestriction[]).map((diet) => {
            const selected = prefs.dietaryRestrictions.includes(diet);
            return (
              <ChipButton
                key={diet}
                label={dietaryLabels[diet].label}
                selected={selected}
                onClick={() => toggleMulti("dietaryRestrictions", diet)}
              />
            );
          })}
        </div>
      </PreferenceSection>

      {/* Save button */}
      <div className="flex items-center justify-end gap-3 border-t border-border pt-6">
        {saved && (
          <span className="text-xs text-amber-500 animate-fade-in">
            偏好设置功能即将上线，敬请期待
          </span>
        )}
        <button
          onClick={handleSave}
          className={`inline-flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-medium text-white transition-all ${
            saved
              ? "bg-amber-500 hover:bg-amber-600"
              : "bg-primary hover:bg-primary-dark"
          }`}
        >
          {saved ? (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              即将上线
            </>
          ) : (
            "保存偏好设置"
          )}
        </button>
      </div>
    </div>
  );
}

// ----- Sub-components -----

/** Section wrapper with title, description and icon */
function PreferenceSection({
  title,
  description,
  icon,
  children,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-card-foreground">{title}</h3>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

/** Toggleable chip button for multi-select */
function ChipButton({
  label,
  selected,
  onClick,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-all ${
        selected
          ? "border-primary bg-primary/10 text-primary"
          : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground"
      }`}
    >
      {label}
    </button>
  );
}

/** Card-style radio for single-select */
function RadioCard({
  label,
  description,
  selected,
  onClick,
}: {
  label: string;
  description: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-start rounded-lg border p-3 text-left transition-all ${
        selected
          ? "border-primary bg-primary/5 ring-1 ring-primary/20"
          : "border-border hover:border-primary/30"
      }`}
    >
      <div className="flex w-full items-center justify-between">
        <span
          className={`text-sm font-semibold ${
            selected ? "text-primary" : "text-card-foreground"
          }`}
        >
          {label}
        </span>
        {selected && (
          <svg className="h-4 w-4 text-primary" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        )}
      </div>
      <span className="mt-0.5 text-xs text-muted-foreground">{description}</span>
    </button>
  );
}

// ----- Icon components -----

function MountainIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 20.25L10.5 6l4.5 8.25L18 10.5 21 20.25H3z" />
    </svg>
  );
}

function WalletIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a2.25 2.25 0 00-2.25-2.25H15a3 3 0 11-6 0H5.25A2.25 2.25 0 003 12m18 0v6a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 9m18 0V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v3" />
    </svg>
  );
}

function BuildingIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21" />
    </svg>
  );
}

function PlaneIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
    </svg>
  );
}

function UtensilsIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8.25v-1.5m0 1.5c-1.355 0-2.697.056-4.024.166C6.845 8.51 6 9.473 6 10.608v2.513m6-4.871c1.355 0 2.697.056 4.024.166C17.155 8.51 18 9.473 18 10.608v2.513M15 8.25v-1.5m-6 1.5v-1.5m12 9.75l-1.5.75a3.354 3.354 0 01-3 0 3.354 3.354 0 00-3 0 3.354 3.354 0 01-3 0 3.354 3.354 0 00-3 0 3.354 3.354 0 01-3 0L3 16.5m15-3.379a48.474 48.474 0 00-6-.371c-2.032 0-4.034.126-6 .371m12 0c.39.049.777.102 1.163.16 1.07.16 1.837 1.094 1.837 2.175v5.169c0 .621-.504 1.125-1.125 1.125H4.125A1.125 1.125 0 013 20.625v-5.17c0-1.08.768-2.014 1.837-2.174A47.78 47.78 0 016 13.12M16.5 8.25V6.75a4.5 4.5 0 10-9 0v1.5" />
    </svg>
  );
}
