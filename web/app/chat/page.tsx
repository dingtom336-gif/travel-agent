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
      <div className="flex h-[calc(100dvh-4rem)] bg-surface">
        {/* Main chat area */}
        <div className="flex flex-1 flex-col">
          <Suspense fallback={<ChatLoading />}>
            <ChatContainer />
          </Suspense>
        </div>

        {/* Right sidebar - Itinerary preview (PC only) */}
        <aside className="hidden w-80 flex-shrink-0 border-l border-outline-variant/30 bg-surface-container-low lg:block xl:w-96">
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
    <div className="flex flex-1 flex-col bg-surface">
      <div className="flex-1 overflow-hidden px-3 py-4 sm:px-6 sm:py-8">
        <div className="mx-auto max-w-4xl space-y-8 animate-pulse">
          {/* User message skeleton */}
          <div className="flex justify-end">
            <div className="flex max-w-[70%] gap-2 flex-row-reverse">
              <div className="h-8 w-8 shrink-0 rounded-full bg-surface-container-highest" />
              <div className="rounded-2xl rounded-tr-sm bg-primary/20 px-4 py-3 w-48 h-10" />
            </div>
          </div>
          {/* AI message skeleton */}
          <div className="flex justify-start">
            <div className="flex max-w-[80%] gap-2">
              <div className="h-8 w-8 shrink-0 rounded-full bg-surface-container-highest" />
              <div className="flex flex-col gap-2 flex-1">
                <div className="rounded-2xl rounded-tl-sm bg-surface-container-high px-4 py-3 space-y-2">
                  <div className="h-3 w-3/4 rounded bg-on-surface/10" />
                  <div className="h-3 w-full rounded bg-on-surface/10" />
                  <div className="h-3 w-2/3 rounded bg-on-surface/10" />
                </div>
              </div>
            </div>
          </div>
          {/* Second user message skeleton */}
          <div className="flex justify-end">
            <div className="flex max-w-[70%] gap-2 flex-row-reverse">
              <div className="h-8 w-8 shrink-0 rounded-full bg-surface-container-highest" />
              <div className="rounded-2xl rounded-tr-sm bg-primary/20 px-4 py-3 w-32 h-10" />
            </div>
          </div>
          {/* Second AI message skeleton */}
          <div className="flex justify-start">
            <div className="flex max-w-[80%] gap-2">
              <div className="h-8 w-8 shrink-0 rounded-full bg-surface-container-highest" />
              <div className="flex flex-col gap-2 flex-1">
                <div className="rounded-2xl rounded-tl-sm bg-surface-container-high px-4 py-3 space-y-2">
                  <div className="h-3 w-full rounded bg-on-surface/10" />
                  <div className="h-3 w-5/6 rounded bg-on-surface/10" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      {/* Input bar skeleton */}
      <div className="border-t border-outline-variant/30 px-3 py-3 sm:px-6">
        <div className="mx-auto max-w-4xl">
          <div className="h-12 rounded-2xl bg-surface-container-high animate-pulse" />
        </div>
      </div>
    </div>
  );
}
