import { useSyncExternalStore } from 'react'

/* Light by default (a projector in a lit room); dark on request. The choice is remembered per browser. */
export type Theme = 'dark' | 'light'
const KEY = 'indicbridge-theme'
const listeners = new Set<() => void>()

export const getTheme = (): Theme => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')

export function setTheme(t: Theme) {
  if (t === 'dark') document.documentElement.dataset.theme = 'dark'
  else delete document.documentElement.dataset.theme
  try {
    localStorage.setItem(KEY, t)
  } catch {
    /* private mode: the choice just isn't remembered */
  }
  listeners.forEach((l) => l())
}

export function initTheme() {
  try {
    if (localStorage.getItem(KEY) === 'dark') document.documentElement.dataset.theme = 'dark'
  } catch {
    /* ignore */
  }
}

export function useTheme(): Theme {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    getTheme,
    () => 'light',
  )
}
