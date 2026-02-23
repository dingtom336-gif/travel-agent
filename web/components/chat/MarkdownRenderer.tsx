"use client";

import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import type { Components } from "react-markdown";

/**
 * Rich markdown renderer using react-markdown with GFM tables,
 * raw HTML support, and custom Tailwind-styled elements.
 */
const markdownComponents: Components = {
  // Table styling
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th className="px-3 py-2 text-left font-medium">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border-t border-border/50 px-3 py-2">{children}</td>
  ),
  // Image with error fallback
  img: ({ src, alt }) => (
    <ImageWithFallback src={String(src || "")} alt={String(alt || "")} />
  ),
  // Link styling
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline decoration-primary/30 hover:decoration-primary transition-colors break-all"
    >
      {children}
    </a>
  ),
  // Blockquote
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-3 border-primary/40 pl-3 text-muted-foreground italic">
      {children}
    </blockquote>
  ),
  // Code blocks + inline code
  code: ({ className, children }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <pre className="my-2 overflow-x-auto rounded-lg bg-foreground/5 p-3 text-xs">
          <code className={className}>{children}</code>
        </pre>
      );
    }
    return (
      <code className="rounded bg-foreground/10 px-1.5 py-0.5 text-xs font-mono">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <>{children}</>,
  // Headings
  h1: ({ children }) => <h2 className="mt-4 mb-1.5 text-base font-bold">{children}</h2>,
  h2: ({ children }) => <h3 className="mt-3 mb-1 text-base font-bold">{children}</h3>,
  h3: ({ children }) => <h4 className="mt-3 mb-1 text-sm font-semibold">{children}</h4>,
  h4: ({ children }) => <h5 className="mt-2 mb-1 text-sm font-medium">{children}</h5>,
  // Lists
  ul: ({ children }) => <ul className="my-1 space-y-0.5 pl-4 list-disc marker:text-muted-foreground">{children}</ul>,
  ol: ({ children }) => <ol className="my-1 space-y-0.5 pl-4 list-decimal marker:text-muted-foreground">{children}</ol>,
  li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
  // Paragraphs
  p: ({ children }) => <p className="my-1.5 leading-relaxed break-words">{children}</p>,
  // Horizontal rule as visual divider
  hr: () => <hr className="my-3 border-border/60" />,
  // Strong / emphasis
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
};

export default function MarkdownRenderer({ content }: { content: string }) {
  if (!content) return null;
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
      components={markdownComponents}
    >
      {content}
    </ReactMarkdown>
  );
}

/**
 * Image component with gradient fallback on load error.
 */
function ImageWithFallback({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  const handleError = useCallback(() => setFailed(true), []);

  if (failed) {
    return (
      <div className="my-2 flex h-40 w-full items-center justify-center rounded-xl bg-gradient-to-br from-blue-50 to-cyan-50 text-sm text-muted-foreground">
        {alt || "Image"}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className="my-2 max-w-full rounded-xl shadow-sm"
      loading="lazy"
      onError={handleError}
    />
  );
}
