/**
 * Empty state shown when no messages yet.
 */
export default function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-10 text-center sm:py-16">
      <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 sm:mb-4 sm:h-16 sm:w-16">
        <svg className="h-7 w-7 text-primary sm:h-8 sm:w-8" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
        </svg>
      </div>
      <h3 className="mb-2 text-base font-semibold text-foreground sm:text-lg">
        开始规划你的旅行
      </h3>
      <p className="max-w-md text-sm text-muted-foreground">
        告诉我你想去哪里、什么时候出发、几个人同行，我会为你规划最佳旅行方案。
      </p>
    </div>
  );
}
