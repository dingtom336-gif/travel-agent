"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { ChatMessage as ChatMessageType, AgentStatus as AgentStatusType } from "@/lib/types";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import AgentStatus from "./AgentStatus";

// Generate unique ID for messages
function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

// Mock streaming response for demo purposes
async function mockStreamResponse(
  userMessage: string,
  onAgentStatus: (status: AgentStatusType) => void,
  onTextChunk: (text: string) => void,
  onDone: () => void,
  signal?: AbortSignal
): Promise<void> {
  const delay = (ms: number) =>
    new Promise<void>((resolve, reject) => {
      const timer = setTimeout(resolve, ms);
      signal?.addEventListener("abort", () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      });
    });

  try {
    // Simulate agent thinking
    onAgentStatus({ agent: "orchestrator", task: "正在分析你的需求...", status: "running" });
    await delay(800);
    onAgentStatus({ agent: "orchestrator", task: "正在分析你的需求...", status: "done" });

    // Simulate parallel agent execution
    onAgentStatus({ agent: "transport", task: "正在搜索机票信息...", status: "running" });
    onAgentStatus({ agent: "weather", task: "正在查询目的地天气...", status: "running" });
    await delay(1200);
    onAgentStatus({ agent: "weather", task: "正在查询目的地天气...", status: "done" });
    await delay(600);
    onAgentStatus({ agent: "transport", task: "正在搜索机票信息...", status: "done" });

    onAgentStatus({ agent: "poi", task: "正在推荐热门景点...", status: "running" });
    await delay(1000);
    onAgentStatus({ agent: "poi", task: "正在推荐热门景点...", status: "done" });

    onAgentStatus({ agent: "itinerary", task: "正在编排行程方案...", status: "running" });
    await delay(800);
    onAgentStatus({ agent: "itinerary", task: "正在编排行程方案...", status: "done" });

    // Generate mock response based on user message
    const responseText = generateMockResponse(userMessage);

    // Stream text character by character
    for (let i = 0; i < responseText.length; i++) {
      if (signal?.aborted) return;
      onTextChunk(responseText[i]);
      // Vary speed slightly for natural feel
      await delay(15 + Math.random() * 25);
    }

    onDone();
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return;
    }
    throw error;
  }
}

// Generate a plausible mock response
function generateMockResponse(userMessage: string): string {
  if (userMessage.includes("孩子") || userMessage.includes("亲子")) {
    return `## 亲子游推荐方案

根据你的需求，我为你推荐以下几个适合亲子游的目的地：

### 1. 三亚
- **适合年龄**: 2-12岁
- **推荐天数**: 4-5天
- **亮点**: 亚龙湾沙滩、海昌梦幻海洋不夜城、南山文化旅游区
- **预算参考**: 人均3000-5000元

### 2. 成都
- **适合年龄**: 3岁以上
- **推荐天数**: 3-4天
- **亮点**: 大熊猫繁育研究基地、都江堰、宽窄巷子
- **预算参考**: 人均2500-4000元

### 3. 上海迪士尼
- **适合年龄**: 4岁以上
- **推荐天数**: 2-3天
- **亮点**: 迪士尼乐园、上海科技馆、外滩
- **预算参考**: 人均2000-3500元

需要我为你详细规划其中某个目的地的行程吗？可以告诉我你的出发城市、出行时间和预算，我来帮你安排。`;
  }

  if (userMessage.includes("周末") || userMessage.includes("短途")) {
    return `## 周末短途游推荐

为你推荐几个适合周末2-3天的短途旅行目的地：

### 近郊自然类
- **莫干山**: 民宿、竹林、户外运动，适合放松
- **千岛湖**: 环湖骑行、垂钓、湖鲜美食
- **黄山**: 经典徒步，日出云海，2天可游

### 文化探索类
- **苏州**: 园林、古镇、评弹，江南韵味
- **杭州**: 西湖、灵隐寺、龙井茶园
- **南京**: 中山陵、夫子庙、鸡鸣寺

### 快速出行建议
1. 提前订好往返交通（高铁优先）
2. 周五晚出发，周日晚返回
3. 住宿选在景区附近，减少通勤
4. 不贪多，每天2-3个景点即可

告诉我你的出发城市，我可以帮你规划具体路线和时间安排！`;
  }

  if (userMessage.includes("出国") || userMessage.includes("签证") || userMessage.includes("国外")) {
    return `## 出境旅行规划指南

### 热门出境目的地推荐

**东南亚（入门级）**
- 泰国: 落地签，5-7天，人均5000-8000元
- 日本: 需签证，5-7天，人均8000-15000元
- 新加坡: 需签证，3-5天，人均6000-10000元

### 出行准备清单
1. **护照**: 确保有效期6个月以上
2. **签证**: 提前1-2个月办理
3. **机票**: 建议提前1-2个月预订
4. **住宿**: Booking/Agoda 比价预订
5. **保险**: 建议购买境外旅行保险
6. **通讯**: 提前购买当地SIM卡或开通国际漫游

### 省钱技巧
- 关注航司会员日和促销
- 淡季出行，价格可低30-50%
- 选择当地公共交通
- 住民宿或青旅

你想去哪个国家？告诉我具体目的地，我帮你做详细攻略！`;
  }

  // Default response
  return `## 旅行规划方案

感谢你的信任！我已经分析了你的需求，这是我的初步建议：

### 行程概览
根据你的描述，我推荐以下规划方向：

1. **目的地选择**: 根据你的偏好，会为你筛选最合适的目的地
2. **交通安排**: 综合考虑时间和预算，推荐最优出行方式
3. **住宿推荐**: 位置便利、性价比高的住宿选择
4. **景点规划**: 经典与小众结合，避免人挤人

### 下一步
为了给你更精准的方案，可以补充以下信息：
- **出发城市**: 方便查询交通
- **出行日期**: 影响价格和天气
- **同行人数**: 影响预算分配
- **特殊需求**: 如饮食禁忌、无障碍需求等

随时告诉我更多细节，我会持续优化方案！`;
}

export default function ChatContainer() {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatusType[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const initialPromptHandled = useRef(false);

  // Auto-scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, agentStatuses, scrollToBottom]);

  // Handle sending a message (both user-initiated and auto from URL param)
  const handleSend = useCallback(async (text: string) => {
    if (isProcessing) return;

    // Add user message
    const userMsg: ChatMessageType = {
      id: generateId(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);
    setAgentStatuses([]);

    // Create abort controller for this request
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Create placeholder for AI response
    const aiMsgId = generateId();
    const aiMsg: ChatMessageType = {
      id: aiMsgId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isStreaming: true,
    };
    setMessages((prev) => [...prev, aiMsg]);

    try {
      await mockStreamResponse(
        text,
        // Agent status callback
        (status) => {
          setAgentStatuses((prev) => {
            const existing = prev.findIndex(
              (s) => s.agent === status.agent && s.task === status.task
            );
            if (existing >= 0) {
              const updated = [...prev];
              updated[existing] = status;
              return updated;
            }
            return [...prev, status];
          });
        },
        // Text chunk callback
        (chunk) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMsgId
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          );
        },
        // Done callback
        () => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMsgId ? { ...msg, isStreaming: false } : msg
            )
          );
          setAgentStatuses([]);
          setIsProcessing(false);
        },
        controller.signal
      );
    } catch {
      setIsProcessing(false);
      setAgentStatuses([]);
    }
  }, [isProcessing]);

  // Handle initial prompt from URL query parameter
  useEffect(() => {
    if (initialPromptHandled.current) return;
    const q = searchParams.get("q");
    if (q) {
      initialPromptHandled.current = true;
      // Small delay to ensure component is mounted
      const timer = setTimeout(() => {
        handleSend(q);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [searchParams, handleSend]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {messages.length === 0 && (
            <EmptyState />
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Agent status indicators */}
          {agentStatuses.length > 0 && (
            <AgentStatus statuses={agentStatuses} />
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <ChatInput onSend={handleSend} disabled={isProcessing} />
    </div>
  );
}

/**
 * Empty state shown when no messages yet.
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
        <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
        </svg>
      </div>
      <h3 className="mb-2 text-lg font-semibold text-foreground">
        开始规划你的旅行
      </h3>
      <p className="max-w-md text-sm text-muted-foreground">
        告诉我你想去哪里、什么时候出发、几个人同行，
        <br />
        我会为你规划最佳旅行方案。
      </p>
    </div>
  );
}
