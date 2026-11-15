import { Pause, Play, Cpu } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { LaneTable, MethodSwatch } from '@/components/Lanes'
import { MarkKey, Transcript } from '@/components/Transcript'
import { Select } from '@/components/Select'
import { api, LANGUAGE_NAMES, whisperToken, type Clip, type Language, type Lanes, type TestSet, type Transcription } from '@/lib/api'
import { useStatus } from '@/lib/useStatus'
import { cn } from '@/lib/utils'

interface LiveRun extends Transcription {
  model: string
  label: string
  utt_id: string
}

/**
 * The bench: any test clip, every scored model's output with errors marked, and a live re-run
 * of any built model on this Mac's GPU.
 */
export function Bench() {
  const { status } = useStatus()
  const [language, setLanguage] = useState<Language>('odia')
  const [testSet, setTestSet] = useState<TestSet>('fleurs')
  const [clips, setClips] = useState<Clip[]>([])
  const [query, setQuery] = useState('')
  // A clip id only means something inside its own test set: keep them together so a language
  // switch can never ask for the old language's clip.
  const [picked, setPicked] = useState<{ key: string; utt: string } | null>(null)
  const setKey = `${language}/${testSet}`
  const selected = picked?.key === setKey ? picked.utt : null
  const setSelected = (utt: string) => setPicked({ key: setKey, utt })
  const [lanes, setLanes] = useState<Lanes | null>(null)
  const [live, setLive] = useState<LiveRun[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [precision, setPrecision] = useState<'fp16' | 'q4'>('fp16')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const key = `${language}/${testSet}`
    setClips([])
    setError(null)
    api.clips(language, testSet).then((d) => setClips(d.clips)).catch((e) => setError(e instanceof Error ? e.message : String(e)))
    api.lanes(language, testSet).then((d) => setPicked({ key, utt: d.utt_id })).catch(() => undefined)
  }, [language, testSet])

  useEffect(() => {
    if (!selected) return
    setLanes(null)
    api
      .lanes(language, testSet, selected)
      .then((d) => {
        setLanes(d)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [selected, language, testSet])

  const models = useMemo(() => {
    const m = status?.models ?? {}
    return Object.entries(m)
      .filter(([, e]) => e.language === language || e.language === 'all')
      .map(([id, e]) => ({ id, e, label: id === 'zeroshot' ? 'Zero-shot' : id === 'P-hindi' ? 'Hindi pivot' : e.pivot === 'none' ? 'direct' : `${e.pivot[0].toUpperCase()}${e.pivot.slice(1)} → ${LANGUAGE_NAMES[language].en}` }))
  }, [status, language])

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    return q ? clips.filter((c) => c.text.toLowerCase().includes(q) || String(c.index + 1) === q) : clips
  }, [clips, query])

  const run = async (model: string, label: string, token: string) => {
    if (!selected) return
    setBusy(model)
    setError(null)
    try {
      const res = await api.transcribe({ model, language, token: token === 'per language' ? whisperToken(language) : token, precision, test_set: testSet, utt_id: selected })
      setLive((l) => [{ ...res, model, label: `${label} · ${precision}`, utt_id: selected }, ...l].slice(0, 12))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(null)
    }
  }

  const names = LANGUAGE_NAMES[language]
  const liveHere = live.filter((r) => r.utt_id === selected)

  return (
    <section id="bench" className="border-t border-line bg-paper" aria-labelledby="bench-title">
      <div className="mx-auto max-w-6xl px-5 py-28 sm:px-8 sm:py-36">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <h2 id="bench-title" className="display text-[2.25rem] sm:text-[3.5rem]">
            Any clip. <span className="hand">Every model.</span>
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={language}
              onChange={setLanguage}
              options={(['hindi', 'marathi', 'kannada', 'odia'] as Language[]).map((l) => [l, LANGUAGE_NAMES[l].en])}
              label="Language"
            />
            <div role="radiogroup" aria-label="Test set" className="inline-flex rounded-full border border-line-strong p-0.5">
              {(['fleurs', 'kathbath'] as TestSet[]).map((t) => (
                <button key={t} type="button" role="radio" aria-checked={testSet === t} onClick={() => setTestSet(t)} className={cn('press rounded-full px-3.5 py-1.5 text-[0.8125rem]', testSet === t ? 'bg-ink text-paper' : 'text-muted hover:text-ink')}>
                  {t === 'fleurs' ? 'FLEURS' : 'Kathbath'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && <p className="mt-4 text-sm text-alert">{error}</p>}

        <div className="mt-12 grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
          <div className="flex min-h-0 flex-col overflow-hidden rounded-[14px] border border-line bg-surface">
            <label className="border-b border-line p-2">
              <span className="sr-only">Filter clips</span>
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`Filter ${clips.length} clips`} className="w-full rounded-full border border-line bg-paper px-3.5 py-1.5 text-[0.8125rem] placeholder:text-muted" />
            </label>
            <ol className="max-h-[28rem] overflow-y-auto lg:max-h-[40rem]" aria-label="Test clips">
              {shown.length === 0 && <li className="p-3 text-sm text-muted">{clips.length ? 'No clip matches.' : 'Loading clips…'}</li>}
              {shown.map((c) => (
                <li key={c.utt_id}>
                  <button
                    type="button"
                    onClick={() => setSelected(c.utt_id)}
                    aria-current={selected === c.utt_id}
                    className={cn('grid w-full grid-cols-[2.75rem_minmax(0,1fr)_2.75rem] items-baseline gap-2 border-b border-line px-3 py-2 text-left text-sm hover:bg-sunken', selected === c.utt_id && 'bg-brand-tint')}
                  >
                    <span className="num text-xs text-muted">{c.index + 1}</span>
                    <span className="script truncate" lang={names.lang}>{c.text}</span>
                    <span className="num text-right text-xs text-muted">{c.duration.toFixed(1)}s</span>
                  </button>
                </li>
              ))}
            </ol>
          </div>

          <div className="min-w-0 rounded-[14px] border border-line bg-surface p-5 sm:p-6">
            {!lanes ? (
              <p className="text-sm text-muted">Loading the clip…</p>
            ) : (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <ClipPlayer url={api.audioUrl(language, testSet, lanes.utt_id)} />
                  <span className="num text-xs text-muted" title={lanes.utt_id}>
                    clip {(clips.find((c) => c.utt_id === lanes.utt_id)?.index ?? 0) + 1} · {testSet === 'fleurs' ? 'FLEURS' : 'Kathbath'}
                  </span>
                </div>
                <div className="mt-5">
                  <LaneTable
                    key={lanes.utt_id}
                    reference={lanes.reference}
                    lanes={lanes.lanes}
                    language={language}
                    ignite
                    extra={liveHere.map((r, i) => (
                      <tr key={i} className="max-sm:grid max-sm:grid-cols-[minmax(0,1fr)_auto_auto] max-sm:gap-x-3">
                        <th scope="row" className="py-2.5 pr-3 align-top text-sm font-medium max-sm:pb-0">
                          <span className="flex items-center gap-2">
                            <Cpu className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
                            {r.label}
                          </span>
                          <span className="num mt-1 block text-[0.6875rem] font-normal text-muted">
                            live · {r.elapsed.toFixed(2)} s · {r.rtf.toFixed(2)}× · {r.model_mb} MB
                          </span>
                        </th>
                        <td className="py-2.5 pr-3 max-sm:col-span-3 max-sm:row-start-2 max-sm:pt-1">
                          <Transcript ops={r.ops} ignite lang={names.lang} className="text-[1.0625rem]" />
                        </td>
                        <td className="num py-2.5 text-right align-top text-sm max-sm:col-start-2 max-sm:row-start-1 max-sm:pb-0">
                          <span className="text-muted sm:hidden">WER </span>{r.wer?.toFixed(0) ?? '–'}
                        </td>
                        <td className="num py-2.5 text-right align-top text-sm max-sm:col-start-3 max-sm:row-start-1 max-sm:pb-0">
                          <span className="text-muted sm:hidden">CER </span>{r.cer?.toFixed(0) ?? '–'}
                        </td>
                      </tr>
                    ))}
                  />
                </div>
                <MarkKey className="mt-4" />

                <div className="mt-6 border-t border-line pt-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="mr-1 text-[0.8125rem] text-ink">run live</span>
                    {models.length === 0 && <span className="text-sm text-muted">No model built for {names.en} yet (deploy/build_models.py).</span>}
                    {models.map(({ id, e, label }) => (
                      <button
                        key={id}
                        type="button"
                        disabled={busy !== null}
                        onClick={() => run(id, label, e.token)}
                        className="press inline-flex items-center gap-2 rounded-full border border-line-strong px-3.5 py-1.5 text-[0.8125rem] hover:border-brand disabled:opacity-50"
                      >
                        <MethodSwatch pivot={e.pivot} method={e.method} />
                        {busy === id ? 'Transcribing…' : label === 'Zero-shot' ? 'zero-shot' : label}
                      </button>
                    ))}
                    <span className="ml-auto inline-flex items-center gap-2 text-[0.8125rem] text-muted">
                      Weights
                      <Select value={precision} onChange={setPrecision} options={[['fp16', 'fp16'], ['q4', '4-bit']]} label="Weights" />
                    </span>
                  </div>
                  <p className="hand mt-3 text-[0.875rem] text-muted">live runs use MLX, so a word can differ from the scored row</p>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

function ClipPlayer({ url }: { url: string }) {
  const el = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [t, setT] = useState(0)
  const [d, setD] = useState(0)
  useEffect(() => {
    setPlaying(false)
    setT(0)
  }, [url])
  return (
    <div className="flex items-center gap-3">
      <audio
        ref={el}
        src={url}
        preload="metadata"
        onTimeUpdate={(e) => setT(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => setD(e.currentTarget.duration)}
        onEnded={() => setPlaying(false)}
      />
      <button
        type="button"
        onClick={() => {
          const a = el.current
          if (!a) return
          if (playing) a.pause()
          else void a.play()
          setPlaying(!playing)
        }}
        className="press grid h-9 w-9 place-items-center rounded-full bg-brand text-brand-ink"
        aria-label={playing ? 'Pause the clip' : 'Play the clip'}
      >
        {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 translate-x-px" />}
      </button>
      <div className="h-1 w-40 overflow-hidden rounded-full bg-line" aria-hidden="true">
        <div className="h-full bg-brand" style={{ width: `${d ? (100 * t) / d : 0}%` }} />
      </div>
      <span className="num text-xs text-muted">
        {t.toFixed(1)} / {d ? d.toFixed(1) : '–'} s
      </span>
    </div>
  )
}
