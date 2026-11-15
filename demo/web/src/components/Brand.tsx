/**
 * IndicBridge. The mark is an arch on three piers: one language carrying
 * another across. Drawn, not a glyph, so it holds at every size.
 */
export function Mark({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <path d="M3.5 22.5C7 12.6 25 12.6 28.5 22.5" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M3 22.5h26" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M10 22.5v-4.6M16 22.5V16M22 22.5v-4.6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

export function Wordmark() {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Mark className="h-7 w-7 shrink-0 text-brand" />
      <span className="font-display text-[1.0625rem] font-extrabold leading-none tracking-[-0.03em] text-ink [font-stretch:112%]">IndicBridge</span>
    </span>
  )
}
