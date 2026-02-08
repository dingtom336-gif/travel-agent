"use client";

import { Suspense } from "react";
import ChatContainer from "@/components/chat/ChatContainer";
import ItinerarySidebar from "@/components/chat/ItinerarySidebar";
import { TravelPlanProvider } from "@/lib/travel-context";

/**
 * Chat page - the core interaction page.
 * PC: left chat + right sidebar layout.
 * Mobile: single column chat.
 */
export default function ChatPage() {
  return (
    <TravelPlanProvider>
      <div className="flex h-[calc(100vh-4rem)]">
        {/* Main chat area */}
        <div className="flex flex-1 flex-col">
          <Suspense fallback={<ChatLoading />}>
            <ChatContainer />
          </Suspense>
        </div>

        {/* Right sidebar - Itinerary preview (PC only) */}
        <aside className="hidden w-80 flex-shrink-0 border-l border-border bg-muted/30 lg:block xl:w-96">
          <ItinerarySidebar />
        </aside>
      </div>
    </TravelPlanProvider>
  );
}

/**
 * Loading placeholder for chat container.
 */
function ChatLoading() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <svg className="h-8 w-8 animate-spin text-primary" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span className="text-sm text-muted-foreground">加载中...</span>
      </div>
    </div>
  );
}
