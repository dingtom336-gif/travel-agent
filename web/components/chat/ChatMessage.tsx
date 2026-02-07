"use client";

import { ChatMessage as ChatMessageType } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessageType;
}

/**
 * Render a single chat message bubble.
 * User messages: right-aligned, blue bubble.
 * Assistant messages: left-aligned, gray bubble with simple markdown support.
 */
export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex w-full animate-fade-in ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      <div className={`flex max-w-[85%] gap-3 sm:max-w-[75%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-medium ${
            isUser
              ? "bg-primary text-white"
              : "bg-gradient-to-br from-blue-400 to-cyan-400 text-white"
          }`}
        >
          {isUser ? "你" : "AI"}
        </div>

        {/* Message bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-bubble-user text-white"
              : "bg-bubble-ai text-card-foreground"
          } ${message.isStreaming ? "cursor-blink" : ""}`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose-sm">
              <SimpleMarkdown content={message.content} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Simple markdown renderer for AI messages.
 * Supports: bold, inline code, code blocks, line breaks, lists.
 */
function SimpleMarkdown({ content }: { content: string }) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeLines: string[] = [];
  let codeBlockIndex = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block toggle
    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        // End code block
        elements.push(
          <pre
            key={`code-${codeBlockIndex}`}
            className="my-2 overflow-x-auto rounded-lg bg-foreground/5 p-3 text-xs"
          >
            <code>{codeLines.join("\n")}</code>
          </pre>
        );
        codeLines = [];
        inCodeBlock = false;
        codeBlockIndex++;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    // Heading
    if (line.startsWith("### ")) {
      elements.push(
        <h4 key={i} className="mt-3 mb-1 text-sm font-bold">
          {line.slice(4)}
        </h4>
      );
      continue;
    }
    if (line.startsWith("## ")) {
      elements.push(
        <h3 key={i} className="mt-3 mb-1 text-base font-bold">
          {line.slice(3)}
        </h3>
      );
      continue;
    }

    // Unordered list
    if (line.match(/^[\s]*[-*]\s/)) {
      const text = line.replace(/^[\s]*[-*]\s/, "");
      elements.push(
        <div key={i} className="flex gap-2 pl-2">
          <span className="text-muted-foreground">&#x2022;</span>
          <span>{renderInlineMarkdown(text)}</span>
        </div>
      );
      continue;
    }

    // Ordered list
    if (line.match(/^[\s]*\d+\.\s/)) {
      const match = line.match(/^[\s]*(\d+)\.\s(.*)/);
      if (match) {
        elements.push(
          <div key={i} className="flex gap-2 pl-2">
            <span className="text-muted-foreground">{match[1]}.</span>
            <span>{renderInlineMarkdown(match[2])}</span>
          </div>
        );
      }
      continue;
    }

    // Empty line as spacer
    if (!line.trim()) {
      elements.push(<div key={i} className="h-2" />);
      continue;
    }

    // Normal paragraph
    elements.push(
      <p key={i} className="leading-relaxed">
        {renderInlineMarkdown(line)}
      </p>
    );
  }

  return <>{elements}</>;
}

/**
 * Render inline markdown: **bold**, `code`, links
 */
function renderInlineMarkdown(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining) {
    // Bold
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    // Inline code
    const codeMatch = remaining.match(/`([^`]+)`/);

    // Find the earliest match
    const matches = [
      boldMatch ? { type: "bold", match: boldMatch } : null,
      codeMatch ? { type: "code", match: codeMatch } : null,
    ].filter(Boolean) as { type: string; match: RegExpMatchArray }[];

    if (matches.length === 0) {
      parts.push(remaining);
      break;
    }

    // Sort by index position
    matches.sort((a, b) => (a.match.index || 0) - (b.match.index || 0));
    const earliest = matches[0];
    const idx = earliest.match.index || 0;

    // Add text before the match
    if (idx > 0) {
      parts.push(remaining.slice(0, idx));
    }

    if (earliest.type === "bold") {
      parts.push(
        <strong key={`b-${keyIdx++}`} className="font-semibold">
          {earliest.match[1]}
        </strong>
      );
    } else if (earliest.type === "code") {
      parts.push(
        <code
          key={`c-${keyIdx++}`}
          className="rounded bg-foreground/10 px-1.5 py-0.5 text-xs font-mono"
        >
          {earliest.match[1]}
        </code>
      );
    }

    remaining = remaining.slice(idx + earliest.match[0].length);
  }

  return <>{parts}</>;
}
