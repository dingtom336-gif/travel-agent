export default function Footer() {
  return (
    <footer className="border-t border-outline-variant/20 bg-surface-container-low">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold gradient-text font-headline">TravelMind</span>
          </div>
          <p className="text-sm text-on-surface-variant">
            &copy; {new Date().getFullYear()} TravelMind. 你的 AI 旅行规划助手.
            <span className="ml-2 text-[10px] opacity-30 select-none">v0.8.0</span>
          </p>
          <div className="flex gap-4 text-sm text-on-surface-variant">
            <a href="#" className="hover:text-primary transition-colors">关于我们</a>
            <a href="#" className="hover:text-primary transition-colors">隐私政策</a>
            <a href="#" className="hover:text-primary transition-colors">联系我们</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
