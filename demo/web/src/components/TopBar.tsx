import { Menu, Moon, Sun } from 'lucide-react'
import { setTheme, useTheme } from '@/lib/theme'
import { useStatus } from '@/lib/useStatus'
import { Wordmark } from './Brand'

const LINKS = [
  ['#odia', 'odia'],
  ['#results', 'results'],
  ['#bench', 'bench'],
] as const

/**
 * Network state is checked by the server every few seconds. Offline is the claim the demo proves,
 * so the badge says what is true right now rather than a fixed "offline" label.
 */
export function NetworkBadge() {
  const { status, error } = useStatus()
  if (error) return <span className="text-xs text-alert">server not reachable</span>
  if (!status) return null
  return (
    <span className="inline-flex items-center gap-2 text-xs text-muted" title="Inference runs on this Mac either way">
      <span
        className={status.online ? 'h-2 w-2 rounded-full border border-muted' : 'h-2 w-2 rounded-full bg-brand'}
        aria-hidden="true"
      />
      <span className={status.online ? undefined : 'text-ink'}>{status.online ? 'online' : 'offline'}</span>
    </span>
  )
}

export function TopBar() {
  const theme = useTheme()
  return (
    <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between gap-x-6 px-5 pt-5 sm:px-8">
      <a href="#top" aria-label="IndicBridge, top of page" className="rounded-[6px]">
        <Wordmark />
      </a>
      <nav aria-label="Sections" className="flex items-center gap-x-4 text-[0.8125rem] text-muted md:gap-x-6">
        {LINKS.map(([href, label]) => (
          <a key={href} href={href} className="hidden hover:text-ink hover:underline md:inline">
            {label}
          </a>
        ))}
        <details className="relative md:hidden">
          <summary className="press grid h-9 w-9 list-none place-items-center rounded-full border border-line-strong bg-surface text-ink [&::-webkit-details-marker]:hidden" aria-label="Sections">
            <Menu className="h-4 w-4" aria-hidden="true" />
          </summary>
          <ul className="absolute right-0 top-11 z-30 w-44 overflow-hidden rounded-[12px] border border-line bg-surface py-1 text-[0.875rem] text-ink shadow-[var(--shadow-float)]">
            {LINKS.map(([href, label]) => (
              <li key={href}>
                <a href={href} className="block px-4 py-2.5 hover:bg-sunken">{label}</a>
              </li>
            ))}
          </ul>
        </details>
        <NetworkBadge />
        <button
          type="button"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="press grid h-9 w-9 place-items-center rounded-full border border-line-strong bg-surface text-ink hover:border-brand"
          aria-label={theme === 'dark' ? 'Switch to the light theme' : 'Switch to the dark theme'}
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </nav>
    </header>
  )
}
