"use client";

import { useRef, useState, useCallback, useEffect } from "react";

// Only auto-scroll if user is within this distance from bottom
const NEAR_BOTTOM_THRESHOLD = 100;

/**
 * Smart auto-scroll hook that respects user scroll position.
 * During SSE streaming, stops auto-scrolling when user scrolls up.
 */
export function useAutoScroll(deps: unknown[]) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const userScrolledUp = useRef(false);
  const forceNextRef = useRef(false);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const isNearBottom = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight <= NEAR_BOTTOM_THRESHOLD;
  }, []);

  // Track user scroll position
  const handleScroll = useCallback(() => {
    const near = isNearBottom();
    userScrolledUp.current = !near;
    setShowScrollBtn(!near);
  }, [isNearBottom]);

  // Programmatic scroll to bottom
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    messagesEndRef.current?.scrollIntoView({ behavior });
    userScrolledUp.current = false;
    setShowScrollBtn(false);
  }, []);

  // Force scroll on next deps change (e.g. user sends a message)
  const forceScrollOnNext = useCallback(() => {
    forceNextRef.current = true;
  }, []);

  // Auto-scroll when deps change, but only if near bottom
  useEffect(() => {
    if (forceNextRef.current) {
      forceNextRef.current = false;
      scrollToBottom("smooth");
      return;
    }
    if (!userScrolledUp.current) {
      scrollToBottom("instant");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return {
    scrollContainerRef,
    messagesEndRef,
    handleScroll,
    scrollToBottom,
    forceScrollOnNext,
    showScrollBtn,
  };
}
