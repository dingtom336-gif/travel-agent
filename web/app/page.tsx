"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Footer from "@/components/ui/Footer";

// Predefined guide card data
const guideCards = [
  {
    icon: (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.182 15.182a4.5 4.5 0 01-6.364 0M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75zm-.375 0h.008v.015h-.008V9.75zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75zm-.375 0h.008v.015h-.008V9.75z" />
      </svg>
    ),
    title: "带孩子去哪玩？",
    description: "亲子游热门目的地推荐，寓教于乐的旅行方案",
    prompt: "我想带孩子出去玩几天，有什么适合亲子游的目的地推荐吗？",
    color: "from-blue-500/10 to-cyan-500/10 hover:from-blue-500/20 hover:to-cyan-500/20",
    iconColor: "text-blue-500",
  },
  {
    icon: (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    title: "周末短途游",
    description: "两三天就能玩好，说走就走的短途旅行",
    prompt: "这个周末想来个短途游，2-3天的行程，有什么推荐？",
    color: "from-green-500/10 to-emerald-500/10 hover:from-green-500/20 hover:to-emerald-500/20",
    iconColor: "text-green-500",
  },
  {
    icon: (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
      </svg>
    ),
    title: "出国旅行攻略",
    description: "签证、机票、住宿一站式规划，出境无忧",
    prompt: "我想出国旅行，帮我做个完整的出行攻略，包括签证、机票和住宿",
    color: "from-purple-500/10 to-pink-500/10 hover:from-purple-500/20 hover:to-pink-500/20",
    iconColor: "text-purple-500",
  },
  {
    icon: (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zm3 0h.008v.008H18V10.5zm-12 0h.008v.008H6V10.5z" />
      </svg>
    ),
    title: "预算有限怎么玩",
    description: "花小钱也能有大体验，省钱旅行妙招",
    prompt: "预算有限，大概3000块，能去哪里玩3-4天？帮我规划一下",
    color: "from-orange-500/10 to-amber-500/10 hover:from-orange-500/20 hover:to-amber-500/20",
    iconColor: "text-orange-500",
  },
];

export default function Home() {
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");

  // Navigate to chat page with optional preset prompt
  const handleNavigateToChat = (prompt?: string) => {
    const text = prompt || inputValue.trim();
    if (text) {
      router.push(`/chat?q=${encodeURIComponent(text)}`);
    } else {
      router.push("/chat");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleNavigateToChat();
    }
  };

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] flex-col">
      {/* Hero section */}
      <section className="hero-gradient flex flex-1 flex-col items-center justify-center px-4 py-8 sm:py-24">
        <div className="mx-auto w-full max-w-3xl text-center">
          {/* Logo animation area */}
          <div className="mb-4 sm:mb-6 inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-2 text-sm font-medium text-primary">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
            </svg>
            AI 驱动的智能旅行规划
          </div>

          <h1 className="mb-3 sm:mb-4 text-3xl sm:text-4xl font-bold tracking-tight text-foreground lg:text-6xl">
            你的 AI 旅行规划助手
          </h1>
          <p className="mb-6 sm:mb-10 text-base sm:text-lg text-muted-foreground lg:text-xl">
            告诉我你的旅行想法，我来帮你规划完美行程。
            <br className="hidden sm:block" />
            机票、酒店、景点、预算，一次对话全搞定。
          </p>

          {/* Main input area */}
          <div className="relative mx-auto w-full max-w-2xl">
            <div className="flex items-center gap-2 rounded-2xl border border-border bg-card p-2 shadow-lg transition-shadow focus-within:shadow-xl focus-within:ring-2 focus-within:ring-primary/20">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="描述你的旅行计划，例如：去日本5天..."
                aria-label="输入你的旅行计划"
                className="min-w-0 flex-1 bg-transparent px-3 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none sm:px-4 sm:text-base"
              />
              <button
                onPointerDown={(e) => {
                  e.preventDefault();
                  if (inputValue.trim()) handleNavigateToChat();
                }}
                className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary text-white transition-colors hover:bg-primary-dark touch-manipulation ${!inputValue.trim() ? "opacity-40" : ""}`}
                aria-label="发送"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              </button>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              按 Enter 开始对话，或点击下方卡片快速开始
            </p>
          </div>
        </div>
      </section>

      {/* Guide cards section */}
      <section className="bg-background px-4 py-10 sm:py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-8 text-center text-2xl font-bold text-foreground">
            不知道从哪开始？试试这些
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {guideCards.map((card) => (
              <button
                key={card.title}
                onClick={() => handleNavigateToChat(card.prompt)}
                className={`group flex flex-col items-start gap-3 rounded-2xl bg-gradient-to-br ${card.color} border border-border/50 p-4 text-left transition-all hover:border-border hover:shadow-md sm:p-6`}
              >
                <div className={`${card.iconColor}`}>
                  {card.icon}
                </div>
                <h3 className="text-lg font-semibold text-foreground">
                  {card.title}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {card.description}
                </p>
                <span className="mt-auto inline-flex items-center gap-1 text-sm font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                  开始规划
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                  </svg>
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
