"use client";

import { useState, useCallback } from "react";

const STORAGE_KEY = "travelmind_deep_reasoning";

export function useDeepReasoning(): [boolean, (v: boolean) => void] {
  const [enabled, setEnabled] = useState(() => {
    if (typeof window === "undefined") return true;
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === null ? true : stored === "true";
  });

  const toggle = useCallback((v: boolean) => {
    setEnabled(v);
    // F3: move sync I/O out of setState callback path
    queueMicrotask(() => localStorage.setItem(STORAGE_KEY, v ? "true" : "false"));
  }, []);

  return [enabled, toggle];
}
