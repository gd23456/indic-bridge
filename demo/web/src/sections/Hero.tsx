import { Mic, Square, AudioLines, Play, Pause } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import MorphOrb, { type OrbAnswer, type OrbInputApi, type Phase } from '@/components/ui/ai-thiking-orb-and-input'
import { LaneTable } from '@/components/Lanes'
import { Select } from '@/components/Select'
import { Tunnel, type TunnelItem } from '@/components/Tunnel'
import { TopBar } from '@/components/TopBar'
import { Transcript } from '@/components/Transcript'
import { api, bestModel, LANGUAGE_NAMES, whisperToken, type Language, type Lanes, type ModelEntry, type Transcription } from '@/lib/api'
import { MAX_SECONDS, Recorder } from '@/lib/recorder'
import { useStatus } from '@/lib/useStatus'
import { cn } from '@/lib/utils'

type Mode = 'speech' | 'clip'
const LANGS: Language[] = ['odia', 'hindi', 'marathi', 'kannada']

export function Hero() {
  const { status } = useStatus()
  const [language, setLanguage] = useState<Language>('odia')
  const [mode, setMode] = useState<Mode>('clip')
  const [phase, setPhase] = useState<Phase>('idle')
  const [mine, setMine] = useState<TunnelItem[]>([])
  const base = useTestSentences()
  const recording = useRef<Blob | null>(null)
  const statusRef = useRef(status)
  statusRef.current = status

  const onSubmit = async (kind: string): Promise<OrbAnswer> => {
    const names = LANGUAGE_NAMES[language]
    try {
      if (kind === 'clip') {
        const data = await api.lanes(language, 'fleurs')
        // The clip you just played joins the tunnel, entering from the far end
        setMine((m) => [...m.slice(-2), { id: `clip-${data.utt_id}-${Date.now()}`, language, text: data.reference, meta: 'FLEURS', note: 'played just now', mine: true }])
        return {
          title: `${names.en} · typical test clip`,
          done: 'Scored outputs loaded',
          width: 760,
          live: `Reference and ${data.lanes.length} model outputs for a typical ${names.en} clip`,
          node: <ClipCard data={data} />,
        }
      }
      const model = bestModel(statusRef.current?.models ?? {}, language)
      if (!model) return { title: 'No model built yet', text: 'Run deploy/build_models.py to convert a model for this Mac.' }
      if (!recording.current) return { title: 'Nothing recorded', text: 'Press the mic, speak, then press it again.' }
      const token = model.entry.token === 'per language' ? whisperToken(language) : model.entry.token
      const res = await api.transcribe({ model: model.id, language, token, file: recording.current })
      if (res.text) {
        // Your sentence joins the tunnel, entering from the far end
        setMine((m) => [...m.slice(-2), { id: `you-${Date.now()}`, language, text: res.text, meta: `${res.seconds.toFixed(1)} s`, note: 'you, just now', mine: true }])
      }
      return {
        title: `${names.en} · ${modelLabel(model.id, model.entry)}`,
        done: `Done · ${res.elapsed.toFixed(2)} s`,
        width: 620,
        live: `Transcript: ${res.text}`,
        node: <SpeechCard res={res} language={language} />,
      }
    } catch (e) {
      return { title: 'Could not finish', text: e instanceof Error ? e.message : String(e) }
    }
  }

  const idle = phase === 'idle' || phase === 'reset'

  return (
    <section id="top" className="relative isolate overflow-hidden bg-paper" aria-labelledby="hero-title">
      <div className="stage-grid" aria-hidden="true" />
      <div className="stage-wash" aria-hidden="true" />
      <div className="stage-ring" data-ring="inner" aria-hidden="true" />
      <div className="stage-ring" data-ring="outer" aria-hidden="true" />
      <Tunnel items={[...base, ...mine]} calm={!idle} />

      <div className="absolute inset-x-0 top-0 z-20">
        <TopBar />
      </div>

      <div
        className={cn(
          'pointer-events-none absolute inset-x-0 top-[46%] z-10 mx-auto max-w-5xl -translate-y-1/2 px-5 text-center transition-[opacity,transform] duration-500 ease-out sm:px-8',
          idle ? 'opacity-100' : 'scale-[1.06] opacity-0',
        )}
        aria-hidden={!idle}
      >
        {/* a soft pool of paper behind the words, so the sentences fly behind them without crossing them */}
        <div className="hero-veil" aria-hidden="true" />
        <h1 id="hero-title" className="display text-[2.6rem] text-ink sm:text-[4.25rem] lg:text-[5.75rem]">
          Language<span className="-ml-[0.12em]">,</span> <span className="hand block">or just data?</span>
        </h1>
        <p className="mx-auto mt-6 max-w-[34rem] text-balance text-[0.9375rem] leading-relaxed text-muted">
          Whisper, taught Hindi first, then Marathi, Odia and Kannada.
        </p>
      </div>

      <MorphOrb
        className="z-0"
        minThinkMs={0}
        onPhase={setPhase}
        onSubmit={onSubmit}
        copy={{
          labels: [mode === 'speech' ? 'Transcribing on this Mac' : 'Loading the scored outputs'],
          done: 'Done',
          reset: 'Try another',
          answerTitle: 'Result',
        }}
        renderInput={(orb) => (
          <PillControls
            orb={orb}
            language={language}
            setLanguage={setLanguage}
            onMode={(m) => flushSync(() => setMode(m))}
            onRecorded={(b) => (recording.current = b)}
          />
        )}
      />
    </section>
  )
}

/** A few real FLEURS test sentences per language, short enough to read on a card, interleaved. */
function useTestSentences() {
  const [items, setItems] = useState<TunnelItem[]>([])
  useEffect(() => {
    const plan: [Language, number][] = [['odia', 4], ['hindi', 4], ['kannada', 3], ['marathi', 3]]
    Promise.all(
      plan.map(([l, n]) =>
        api.clips(l, 'fleurs').then((d) => {
          const pool = d.clips.filter((c) => c.text.length >= 28 && c.text.length <= 90)
          const step = pool.length / n
          return Array.from({ length: Math.min(n, pool.length) }, (_, i) => pool[Math.floor(i * step)]).map(
            (c): TunnelItem => ({ id: `${l}/${c.utt_id}`, language: l, text: c.text, meta: `${c.duration.toFixed(1)} s`, note: `FLEURS test · #${c.index + 1}` }),
          )
        }),
      ),
    )
      .then((groups) => {
        const out: TunnelItem[] = []
        for (let i = 0; i < Math.max(...groups.map((g) => g.length)); i++) groups.forEach((g) => g[i] && out.push(g[i]))
        setItems(out)
      })
      .catch(() => setItems([]))
  }, [])
  return items
}

function modelLabel(id: string, entry: ModelEntry) {
  if (id === 'zeroshot') return 'zero-shot whisper-base'
  if (id === 'P-hindi') return 'the Hindi pivot'
  const pivot = entry.pivot === 'none' ? 'direct' : `${entry.pivot[0].toUpperCase()}${entry.pivot.slice(1)} pivot`
  return `${pivot} model`
}

/* ───────────── the pill: language, recorder, test clip ───────────── */

function PillControls({
  orb,
  language,
  setLanguage,
  onMode,
  onRecorded,
}: {
  orb: OrbInputApi
  language: Language
  setLanguage: (l: Language) => void
  onMode: (m: Mode) => void
  onRecorded: (b: Blob) => void
}) {
  const rec = useRef<Recorder | null>(null)
  const [state, setState] = useState<'idle' | 'starting' | 'recording'>('idle')
  const [levels, setLevels] = useState<number[]>([])
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const names = LANGUAGE_NAMES[language]

  useEffect(() => () => rec.current?.cancel(), [])

  const stop = async () => {
    const r = rec.current
    if (!r) return
    rec.current = null
    const out = await r.stop()
    setState('idle')
    setLevels([])
    if (out.seconds < 0.6) {
      setError('Too short. Speak for at least a second.')
      return
    }
    onRecorded(out.wav)
    onMode('speech')
    orb.submit('speech')
  }

  const start = async () => {
    setError(null)
    setState('starting')
    const r = new Recorder()
    r.onLevel = (level, s) => {
      setLevels((prev) => [...prev.slice(-27), level])
      setSeconds(s)
    }
    r.onAutoStop = () => void stop()
    try {
      await r.start()
      rec.current = r
      setState('recording')
    } catch {
      setState('idle')
      setError('The microphone is blocked. Allow it in the browser, then try again.')
    }
  }

  const recordingNow = state === 'recording'
  return (
    <>
      <Select
        value={language}
        onChange={setLanguage}
        options={LANGS.map((l) => [l, LANGUAGE_NAMES[l].en])}
        label="Language"
        disabled={orb.busy || recordingNow}
        round
      />

      <div className="flex min-w-0 flex-1 items-center gap-3 text-sm" aria-live="polite">
        {recordingNow ? (
          <>
            <span className="flex h-6 items-center gap-[3px]" aria-hidden="true">
              {Array.from({ length: 28 }).map((_, i) => {
                const v = levels[levels.length - 28 + i] ?? 0
                return <i key={i} className="w-[3px] rounded-full bg-brand" style={{ height: `${Math.max(3, v * 24)}px`, opacity: 0.35 + v * 0.65 }} />
              })}
            </span>
            <span className="num shrink-0 text-ink">
              {Math.floor(seconds)}s <span className="text-muted">/ {MAX_SECONDS}s</span>
            </span>
          </>
        ) : error ? (
          <span className="truncate text-alert">{error}</span>
        ) : (
          <span className="truncate text-muted">
            <span className="hidden sm:inline">Speak in {names.en} · </span>
            <span className="script" lang={names.lang}>{names.native}</span>
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={() => {
          onMode('clip')
          orb.submit('clip')
        }}
        disabled={orb.busy || recordingNow}
        className="press flex h-11 shrink-0 items-center gap-2 rounded-full border border-line-strong px-3 text-sm text-ink hover:border-brand disabled:opacity-40"
        aria-label={`Play a typical ${names.en} test clip through every model`}
      >
        <AudioLines className="h-4 w-4" aria-hidden="true" />
        <span className="sm:hidden">Clip</span>
        <span className="hidden sm:inline">Test clip</span>
      </button>

      <button
        type="button"
        onClick={() => (recordingNow ? void stop() : void start())}
        disabled={orb.busy || state === 'starting'}
        className="mo-send"
        data-ready=""
        aria-label={recordingNow ? 'Stop and transcribe' : `Record ${names.en} speech`}
      >
        {recordingNow ? <Square style={{ width: 16, height: 16 }} fill="currentColor" /> : <Mic />}
      </button>
    </>
  )
}

/* ───────────── what the card unfolds into ───────────── */

function ClipCard({ data }: { data: Lanes }) {
  const audio = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  useEffect(() => () => audio.current?.pause(), [])
  const toggle = () => {
    if (!audio.current) {
      audio.current = new Audio(api.audioUrl(data.language, data.test_set, data.utt_id))
      audio.current.onended = () => setPlaying(false)
    }
    if (playing) {
      audio.current.pause()
      setPlaying(false)
    } else {
      void audio.current.play()
      setPlaying(true)
    }
  }
  return (
    <div className="text-left" style={{ '--ignite-delay': '1300ms' } as React.CSSProperties}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <button type="button" onClick={toggle} className="press inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full border border-line-strong px-3 py-1.5 text-sm hover:border-brand">
          {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          {playing ? 'Pause' : 'Play the clip'}
        </button>
        <span className="hand text-sm text-muted">each model's error here is close to its average</span>
      </div>
      <LaneTable reference={data.reference} lanes={data.lanes} language={data.language} ignite orbWords />
    </div>
  )
}

function SpeechCard({ res, language }: { res: Transcription; language: Language }) {
  const names = LANGUAGE_NAMES[language]
  return (
    <div className="text-left">
      {res.text ? (
        <Transcript text={res.text} orbWords lang={names.lang} className="text-[1.375rem] leading-[1.55] text-ink" />
      ) : (
        <p className="text-muted">The model returned no words.</p>
      )}
      <dl className="num mt-5 grid grid-cols-2 gap-x-6 gap-y-3 border-t border-line pt-4 text-xs sm:grid-cols-4">
        <Stat label="time" value={`${res.elapsed.toFixed(2)} s`} note={`for ${res.seconds.toFixed(1)} s of audio`} />
        <Stat label="speed" value={res.rtf > 0 ? `${(1 / res.rtf).toFixed(0)}×` : '–'} note="faster than real time" />
        <Stat
          label="on this mac"
          value={`${res.model_mb.toFixed(0)} MB`}
          note={`${res.precision === 'q4' ? '4-bit' : 'fp16'} · network ${res.online ? 'on' : 'off'}`}
          lit={!res.online}
        />
        <Stat label="script" value={res.script_valid != null ? `${res.script_valid.toFixed(0)}%` : '–'} note={`of letters in ${names.en} script`} />
      </dl>
    </div>
  )
}

function Stat({ label, value, note, lit = false }: { label: string; value: string; note: string; lit?: boolean }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="mt-0.5 text-[1.0625rem] text-ink">{value}</dd>
      <dd className={cn('mt-0.5', lit ? 'text-brand' : 'text-muted')}>{note}</dd>
    </div>
  )
}
