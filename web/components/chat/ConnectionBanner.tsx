import type { ConnectionState } from "@/lib/api-client";

interface ConnectionBannerProps {
  state: ConnectionState;
}

/**
 * Top banner showing SSE connection status.
 * Only visible during reconnecting or failed states.
 */
export default function ConnectionBanner({ state }: ConnectionBannerProps) {
  if (state === "idle" || state === "connecting" || state === "connected") {
    return null;
  }

  const isReconnecting = state === "reconnecting";

  return (
    <div
      className={`flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium ${
        isReconnecting
          ? "bg-yellow-50 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300"
          : "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300"
      }`}
    >
      {isReconnecting ? (
        <>
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
          <span>重新连接中...</span>
        </>
      ) : (
        <>
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <span>连接失败，请重新发送消息</span>
        </>
      )}
    </div>
  );
}
