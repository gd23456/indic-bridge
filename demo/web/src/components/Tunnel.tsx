import { motion, useAnimationFrame, useMotionValue, useReducedMotion, useSpring, useTransform, type MotionValue } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { LANGUAGE_NAMES, type Language } from '@/lib/api'

/**
 * The hero's background: real test sentences on cards, flying out of the vanishing point toward
 * the viewer, after the 21st.dev perspective-tunnel hero. It never captures the wheel: it drifts on
 * its own, page scroll pushes it forward, the pointer pans the camera. A card that arrives later
 * (a live transcript, a clip just played) enters far away, already visible.
 */
export interface TunnelItem {
  id: string
  language: Language
  text: string
  meta: string
  note: string
  mine?: boolean
}

const FLIGHT_S = 44 // seconds for one card to travel from far to near
const SPRING = { stiffness: 60, damping: 25, mass: 0.5 }
const mod1 = (v: number) => ((v % 1) + 1) % 1

interface Stage {
  width: number
  height: number
  mobile: boolean
}

function useStage(): Stage {
  const read = () => ({ width: window.innerWidth, height: window.innerHeight, mobile: window.innerWidth < 768 })
  const [stage, setStage] = useState<Stage>(read)
  useEffect(() => {
    const on = () => setStage(read())
    window.addEventListener('resize', on)
    return () => window.removeEventListener('resize', on)
  }, [])
  return stage
}

function useParallax(enabled: boolean) {
  const rawX = useMotionValue(0)
  const rawY = useMotionValue(0)
  const x = useSpring(rawX, SPRING)
  const y = useSpring(rawY, SPRING)
  useEffect(() => {
    if (!enabled) return
    const on = (e: PointerEvent) => {
      rawX.set((e.clientX / window.innerWidth - 0.5) * 2)
      rawY.set((e.clientY / window.innerHeight - 0.5) * 2)
    }
    window.addEventListener('pointermove', on, { passive: true })
    return () => window.removeEventListener('pointermove', on)
  }, [enabled, rawX, rawY])
  return { x, y }
}

export function Tunnel({ items, calm }: { items: TunnelItem[]; calm: boolean }) {
  const reduce = useReducedMotion() ?? false
  const stage = useStage()
  const travel = useMotionValue(0) // distance flown, in whole flights
  const pace = useRef(1)
  const calmRef = useRef(calm)
  calmRef.current = calm
  const pointer = useParallax(!reduce)

  // Phones get fewer cards. Each card keeps the phase it was given when it first appeared, so
  // adding one never jumps the others.
  const shown = stage.mobile ? [...items.filter((i) => !i.mine).slice(0, 8), ...items.filter((i) => i.mine)] : items
  const phases = useRef(new Map<string, number>())
  if (phases.current.size === 0) shown.forEach((it, i) => phases.current.set(it.id, i / Math.max(1, shown.length)))
  else shown.forEach((it) => phases.current.has(it.id) || phases.current.set(it.id, mod1(0.5 - travel.get())))

  useAnimationFrame((_, delta) => {
    if (reduce) return
    const target = calmRef.current ? 0.18 : 1
    pace.current += (target - pace.current) * Math.min(1, delta / 700)
    travel.set(travel.get() + (Math.min(delta, 64) / 1000 / FLIGHT_S) * pace.current)
  })

  useEffect(() => {
    if (reduce) return
    let last = window.scrollY
    const on = () => {
      const y = window.scrollY
      travel.set(travel.get() + Math.max(-0.05, Math.min(0.05, (y - last) * 0.00035)))
      last = y
    }
    window.addEventListener('scroll', on, { passive: true })
    return () => window.removeEventListener('scroll', on)
  }, [reduce, travel])

  return (
    <div className="tunnel" data-calm={calm ? '' : undefined} aria-hidden="true">
      {/* Two layers: the test sentences, then your own cards drawn above them, so a sentence you
          just added is never hidden behind a nearer test card. */}
      {[false, true].map((layer) => (
        <div key={String(layer)} className="absolute inset-0" style={{ perspective: stage.mobile ? 900 : 1200 }}>
          <div className="absolute inset-0" style={{ transformStyle: 'preserve-3d' }}>
            {shown.map((it, i) =>
              !!it.mine === layer ? (
                <Card
                  key={it.id}
                  item={it}
                  index={i}
                  slot={it.mine ? shown.filter((x) => x.mine).indexOf(it) : -1}
                  phase={phases.current.get(it.id) ?? 0}
                  travel={travel}
                  pointer={pointer}
                  stage={stage}
                />
              ) : null,
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function Card({
  item,
  index,
  slot,
  phase,
  travel,
  pointer,
  stage,
}: {
  item: TunnelItem
  index: number
  slot: number
  phase: number
  travel: MotionValue<number>
  pointer: { x: MotionValue<number>; y: MotionValue<number> }
  stage: Stage
}) {
  // Golden-angle placement round the vanishing point, as in the original tunnel. Your own cards
  // (slot >= 0) take the open lanes either side of the headline, so they are seen the moment they land.
  // Phones have no room beside the headline, so there the lanes run below and above it.
  const lane = stage.mobile ? (slot % 2 === 0 ? 1.2 : -1.9) : slot % 2 === 0 ? -0.3 : Math.PI + 0.3
  const angle = slot >= 0 ? lane : index * 137.5 * (Math.PI / 180)
  const baseX = Math.cos(angle) * stage.width * (slot >= 0 ? (stage.mobile ? 0.3 : 0.44) : 0.27 + (index % 3) * 0.08)
  const baseY = Math.sin(angle) * stage.height * (slot >= 0 ? 0.32 : 0.25 + (index % 2) * 0.09)
  const rotate = (index % 2 === 0 ? 1 : -1) * (2 + (index % 5) * 1.5)
  const width = stage.mobile ? Math.max(130, Math.min(170, stage.width * 0.38)) : Math.max(180, Math.min(240, stage.width * 0.16))
  const far = stage.mobile ? -1200 : -1700
  const near = stage.mobile ? 320 : 480
  const pan = stage.mobile ? 18 : 42

  const local = useTransform(travel, (v) => mod1(v + phase))
  const opacity = useTransform(local, [0, 0.16, 0.8, 0.97], [0, 1, 1, 0])
  const transform = useTransform([local, pointer.x, pointer.y], ([l, px, py]: number[]) => {
    const z = far + (near - far) * l
    return `translate3d(calc(-50% + ${baseX - px * pan}px), calc(-50% + ${baseY - py * pan}px), ${z}px) rotateZ(${rotate}deg)`
  })
  const names = LANGUAGE_NAMES[item.language]

  return (
    <motion.div className="absolute left-1/2 top-1/2 will-change-transform" style={{ width, transform, opacity, zIndex: index + 1 }}>
      <div className="tunnel-card" data-mine={item.mine ? '' : undefined}>
        <span className="flex items-baseline justify-between gap-2 text-[0.6875rem] text-muted">
          <span className="uppercase tracking-[0.12em]">{names.en}</span>
          <span className="num">{item.meta}</span>
        </span>
        <p className="script text-[1.0625rem] leading-[1.55] text-ink" lang={names.lang}>
          {item.text}
        </p>
        <span className={item.mine ? 'hand text-[0.875rem] text-brand' : 'text-[0.6875rem] text-muted'}>{item.note}</span>
      </div>
    </motion.div>
  )
}
