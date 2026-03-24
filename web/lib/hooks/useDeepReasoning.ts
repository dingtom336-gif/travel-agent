"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "travelmind_deep_reasoning";

export function useDeepReasoning(): [boolean, (v: boolean) => void] {
  const [enabled, setEnabled] = useState(false);

  // Hydrate from localStorage after mount to avoid SSR mismatch
  useEffect(() => {
    setEnabled(localStorage.getItem(STORAGE_KEY) === "true");
  }, []);

  const toggle = useCallback((v: boolean) => {
    setEnabled(v);
    localStorage.setItem(STORAGE_KEY, v ? "true" : "false");
  }, []);

  return [enabled, toggle];
}
