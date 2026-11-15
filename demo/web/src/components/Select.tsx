import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

/** A native select (keyboard and screen readers work as usual) with the page's drawn chevron. */
export function Select<T extends string>({
  value,
  onChange,
  options,
  label,
  disabled,
  className,
  round = false,
}: {
  value: T
  onChange: (v: T) => void
  options: [T, string][]
  label: string
  disabled?: boolean
  className?: string
  round?: boolean
}) {
  return (
    <label className={cn('relative inline-flex shrink-0 items-center', className)}>
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        disabled={disabled}
        className={cn(
          'appearance-none rounded-full border border-line-strong py-2 pl-3.5 pr-8 text-[0.8125rem] text-ink hover:border-brand disabled:opacity-50',
          round ? 'bg-transparent' : 'bg-surface',
        )}
      >
        {options.map(([v, text]) => (
          <option key={v} value={v} className="bg-surface text-ink">
            {text}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 h-4 w-4 text-muted" aria-hidden="true" />
    </label>
  )
}
