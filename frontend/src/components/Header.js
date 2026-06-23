
export default function Header() {
  return (
    <header className="w-full border-b border-[var(--color-border-subtle)] bg-[var(--color-surface)]/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--color-accent)] to-[#8b5cf6] flex items-center justify-center shadow-lg shadow-[var(--color-accent)]/20">
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight text-[var(--color-text-primary)] leading-none">
              BG Remover
            </span>
            <span className="text-[10px] text-[var(--color-text-tertiary)] mt-0.5 leading-none">
              AI Background Removal
            </span>
          </div>
        </div>

        
        <div className="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]">
          <span className="relative w-1.5 h-1.5 rounded-full bg-[var(--color-success)] status-dot" />
          <span>AI Online</span>
        </div>
      </div>
    </header>
  );
}
