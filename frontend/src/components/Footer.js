
export default function Footer() {
  return (
    <footer className="w-full border-t border-[var(--color-border-subtle)] mt-auto">
      <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <p className="text-xs text-[var(--color-text-tertiary)]">
          © {new Date().getFullYear()} BG Remover. Powered by AI.
        </p>
        <p className="text-xs text-[var(--color-text-tertiary)]">
          Commercial-grade quality · No watermarks
        </p>
      </div>
    </footer>
  );
}
