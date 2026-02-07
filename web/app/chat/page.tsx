"use client";

import { Suspense } from "react";
import ChatContainer from "@/components/chat/ChatContainer";

/**
 * Chat page - the core interaction page.
 * PC: left chat + right sidebar layout.
 * Mobile: single column chat.
 */
export default function ChatPage() {
  return (
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

/**
 * Placeholder sidebar for itinerary preview.
 * Will be populated with real data once connected to backend.
 */
function ItinerarySidebar() {
  return (
    <div className="flex h-full flex-col">
      {/* Sidebar header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">行程预览</h2>
        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
          实时更新
        </span>
      </div>

      {/* Sidebar content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Empty state */}
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
            <svg className="h-6 w-6 text-muted-foreground" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
            </svg>
          </div>
          <p className="mb-1 text-sm font-medium text-foreground">暂无行程</p>
          <p className="text-xs text-muted-foreground">
            开始对话后，行程会自动在这里生成
          </p>
        </div>

        {/* Placeholder itinerary cards */}
        <div className="mt-4 space-y-3">
          <PlaceholderCard day={1} title="抵达目的地" items={["机场接机", "入住酒店", "周边探索"]} />
          <PlaceholderCard day={2} title="核心景点游览" items={["热门景点A", "当地美食", "文化体验"]} />
          <PlaceholderCard day={3} title="自由活动 & 返程" items={["购物时间", "特色市场", "前往机场"]} />
        </div>
      </div>
    </div>
  );
}

/**
 * A placeholder card for the itinerary sidebar.
 */
function PlaceholderCard({
  day,
  title,
  items,
}: {
  day: number;
  title: string;
  items: string[];
}) {
  return (
    <div className="rounded-xl border border-border/60 bg-card p-3 opacity-40">
      <div className="mb-2 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
          {day}
        </span>
        <span className="text-xs font-medium text-card-foreground">{title}</span>
      </div>
      <div className="space-y-1.5 pl-8">
        {items.map((item) => (
          <div key={item} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <div className="h-1 w-1 rounded-full bg-muted-foreground/50" />
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
