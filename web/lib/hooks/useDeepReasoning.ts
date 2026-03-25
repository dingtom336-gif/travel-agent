"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "travelmind_deep_reasoning";

export function useDeepReasoning(): [boolean, (v: boolean) => void] {
  const [enabled, setEnabled] = useState(true);

  // Hydrate from localStorage after mount — default to true unless explicitly disabled
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    setEnabled(stored === null ? true : stored === "true");
  }, []);

  const toggle = useCallback((v: boolean) => {
    setEnabled(v);
    localStorage.setItem(STORAGE_KEY, v ? "true" : "false");
  }, []);

  return [enabled, toggle];
}
