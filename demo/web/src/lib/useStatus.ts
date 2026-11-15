import { useEffect, useState } from 'react'
import { api, type Status } from './api'

/* One poll for the whole page: network state and which models are built. */
let current: Status | null = null
let error: string | null = null
const listeners = new Set<() => void>()
let timer = 0

async function poll() {
  try {
    current = await api.status()
    error = null
  } catch (e) {
    error = e instanceof Error ? e.message : String(e)
  }
  listeners.forEach((l) => l())
}

export function useStatus() {
  const [, force] = useState(0)
  useEffect(() => {
    const l = () => force((n) => n + 1)
    listeners.add(l)
    if (listeners.size === 1) {
      void poll()
      timer = window.setInterval(poll, 8000)
    }
    return () => {
      listeners.delete(l)
      if (listeners.size === 0) window.clearInterval(timer)
    }
  }, [])
  return { status: current, error }
}
