import { useEffect, useMemo, useState } from 'react'
import { MethodSwatch } from '@/components/Lanes'
import { api, LANGUAGE_NAMES, type Gain, type Language, type ResultRow, type TestSet } from '@/lib/api'
import { useWidth } from '@/lib/useWidth'
import { cn } from '@/lib/utils'

const TARGETS: { language: Language; note: string }[] = [
  { language: 'marathi', note: 'Indo-Aryan · shares Hindi’s script' },
  { language: 'odia', note: 'Indo-Aryan · its own script' },
  { language: 'kannada', note: 'Dravidian · its own script' },
]
const SERIES = [
  { key: 'hindi_pivot', label: 'Hindi pivot', fill: 'var(--pivot-hi)', pivot: 'hindi' },
  { key: 'english_pivot', label: 'English pivot', fill: 'var(--pivot-en)', pivot: 'english' },
] as const

export function Results() {
  const [data, setData] = useState<{ rows: ResultRow[]; gains: Gain[] } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [testSet, setTestSet] = useState<TestSet>('fleurs')
  const [metric, setMetric] = useState<'WER' | 'CER'>('WER')

  useEffect(() => {
    const load = () => api.results().then(setData, (e) => setError(String(e)))
    load()
    const t = window.setInterval(load, 60000) // runs keep finishing while the page is open
    return () => window.clearInterval(t)
  }, [])

  const gains = useMemo(() => (data?.gains ?? []).filter((g) => g.test_set === testSet && g.metric === metric), [data, testSet, metric])
  const anyGain = gains.some((g) => g.points != null)

  return (
    <section id="results" className="mx-auto max-w-6xl px-5 py-28 sm:px-8 sm:py-36" aria-labelledby="results-title">
      <h2 id="results-title" className="display max-w-4xl text-[2.25rem] sm:text-[3.5rem]">
        Hindi helps. <span className="hand">English doesn&apos;t.</span>
      </h2>

      <div className="mt-12 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Segmented value={testSet} onChange={setTestSet} options={[['fleurs', 'FLEURS'], ['kathbath', 'Kathbath']]} label="Test set" />
          <Segmented value={metric} onChange={setMetric} options={[['WER', 'words'], ['CER', 'letters']]} label="Metric" />
        </div>
        <ul className="flex gap-5 text-[0.8125rem]" aria-label="Legend">
          {SERIES.map((s) => (
            <li key={s.key} className="inline-flex items-center gap-2">
              <MethodSwatch pivot={s.pivot} method="multistage_lora" className="h-2.5 w-2.5" />
              {s.label}
            </li>
          ))}
        </ul>
      </div>

      {error && <p className="mt-6 text-sm text-alert">Could not load results: {error}</p>}

      <div className="mt-6 rounded-[14px] border border-line bg-surface p-5 sm:p-7">
        {data && !anyGain ? (
          <p className="text-sm text-muted">No gains yet. They appear as the runs finish; this page re-reads the results every minute.</p>
        ) : (
          <GainChart gains={gains} metric={metric} />
        )}
      </div>
      <p className="hand mt-4 text-[0.9375rem] text-muted">
        {metric === 'WER' ? 'Word' : 'Letter'} errors saved over training on the target alone. Dot: gain. Line: 95% interval. Same 45 hours each.
      </p>

      {data && (
        <details className="group mt-14 border-t border-line pt-6">
          <summary className="flex items-center justify-between gap-3 text-[0.9375rem] text-ink">
            every run, {testSet === 'fleurs' ? 'FLEURS' : 'Kathbath'}
            <span className="text-xs text-muted group-open:hidden">show</span>
            <span className="hidden text-xs text-muted group-open:inline">hide</span>
          </summary>
          <ResultsTable rows={data.rows} testSet={testSet} />
          <ScoringRules rows={data.rows} testSet={testSet} />
        </details>
      )}
    </section>
  )
}

function Segmented<T extends string>({ value, onChange, options, label }: { value: T; onChange: (v: T) => void; options: [T, string][]; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-full border border-line-strong p-0.5">
      {options.map(([v, text]) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={value === v}
          onClick={() => onChange(v)}
          className={cn('press rounded-full px-3.5 py-1.5 text-[0.8125rem]', value === v ? 'bg-ink text-paper' : 'text-muted hover:text-ink')}
        >
          {text}
        </button>
      ))}
    </div>
  )
}

/* Dot-and-whisker, one row per target, one mark per pivot. One axis, zero line, hover for exact values. */
function GainChart({ gains, metric }: { gains: Gain[]; metric: 'WER' | 'CER' }) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null)
  const wide = width >= 560 // narrow charts drop the family note so it never runs into the plot
  const label = wide ? Math.min(280, width * 0.36) : Math.min(96, width * 0.28)
  const right = 24
  const rowH = 76
  const top = 28
  const values = gains.flatMap((g) => (g.points == null ? [] : [g.ci_low ?? g.points, g.ci_high ?? g.points]))
  const lo = Math.min(-2, ...values)
  const hi = Math.max(2, ...values)
  const pad = (hi - lo) * 0.08
  const x = (v: number) => label + ((v - (lo - pad)) / (hi + pad - (lo - pad))) * (width - label - right)
  const step = niceStep(hi - lo)
  const ticks: number[] = []
  for (let t = Math.ceil((lo - pad) / step) * step; t <= hi + pad; t += step) ticks.push(Math.round(t * 100) / 100)
  const height = top + TARGETS.length * rowH

  return (
    <div ref={ref} className="relative mt-4 min-w-0" onMouseLeave={() => setHover(null)}>
      {width > 0 && <svg width={width} height={height} role="img" aria-label={`Transfer gains in ${metric} points with 95% intervals`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={top - 6} y2={height} className={t === 0 ? 'stroke-line-strong' : 'stroke-line'} strokeWidth={1} />
            <text x={x(t)} y={top - 14} textAnchor="middle" className="num fill-muted text-[0.6875rem]">
              {t > 0 ? `+${t}` : t}
            </text>
          </g>
        ))}
        {TARGETS.map(({ language, note }, i) => {
          const y = top + i * rowH + rowH / 2
          return (
            <g key={language}>
              <text x={0} y={wide ? y - 8 : y + 4} className="fill-ink text-[0.9375rem] font-medium">{LANGUAGE_NAMES[language].en}</text>
              {wide && <text x={0} y={y + 12} className="fill-muted text-[0.75rem]">{note}</text>}
              {SERIES.map((s, k) => {
                const g = gains.find((d) => d.language === language && d.gain === s.key)
                const yy = y + (k === 0 ? -9 : 9)
                if (!g || g.points == null) {
                  return (
                    <text key={s.key} x={x(0) + 8} y={yy} dominantBaseline="middle" className="fill-muted text-[0.75rem]">
                      {s.label}: not run yet
                    </text>
                  )
                }
                const text = `${s.label} → ${LANGUAGE_NAMES[language].en}: ${fmtSigned(g.points)} ${metric} points vs direct (95% CI ${fmtSigned(g.ci_low!)} to ${fmtSigned(g.ci_high!)})`
                return (
                  <g
                    key={s.key}
                    onMouseEnter={() => setHover({ x: x(g.points!), y: yy, text })}
                    onFocus={() => setHover({ x: x(g.points!), y: yy, text })}
                    tabIndex={0}
                    role="img"
                    aria-label={text}
                    className="outline-none"
                  >
                    <rect x={x(g.ci_low!) - 6} y={yy - 10} width={Math.max(12, x(g.ci_high!) - x(g.ci_low!) + 12)} height={20} fill="transparent" />
                    <line x1={x(g.ci_low!)} x2={x(g.ci_high!)} y1={yy} y2={yy} stroke={s.fill} strokeWidth={2} strokeLinecap="round" />
                    <circle cx={x(g.points)} cy={yy} r={5} fill={s.fill} className="stroke-surface" strokeWidth={2} />
                  </g>
                )
              })}
            </g>
          )
        })}
      </svg>}
      {hover && (
        <div
          role="tooltip"
          className="pointer-events-none absolute z-10 max-w-xs -translate-x-1/2 -translate-y-full rounded-[8px] border border-line bg-surface px-2.5 py-1.5 text-xs leading-snug text-ink shadow-[var(--shadow-float)]"
          style={{ left: hover.x, top: hover.y - 12 }}
        >
          {hover.text}
        </div>
      )}
    </div>
  )
}

const niceStep = (span: number) => {
  const raw = span / 5
  const p = 10 ** Math.floor(Math.log10(raw || 1))
  return [1, 2, 5, 10].map((m) => m * p).find((s) => s >= raw) ?? p * 10
}
const fmtSigned = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`

const METHOD_ROWS = (language: Language) =>
  language === 'hindi'
    ? [['Z-hindi', 'Zero-shot'], ['P-hindi', 'Fine-tuned (the 45 h pivot)']]
    : [
        [language === 'odia' ? 'Z-odia-bengali' : `Z-${language}`, 'Zero-shot'],
        [`D-${language}`, 'Direct'],
        [`H-${language}`, `Hindi → ${LANGUAGE_NAMES[language].en}`],
        [`E-${language}`, `English → ${LANGUAGE_NAMES[language].en}`],
      ]

function ResultsTable({ rows, testSet }: { rows: ResultRow[]; testSet: TestSet }) {
  const find = (id: string) => rows.find((r) => r.run_id === id && r.test_set === testSet)
  return (
    <div className="mt-6">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[0.6875rem] uppercase tracking-[0.08em] text-muted">
              <th className="py-2 pr-4 font-normal">Language</th>
              <th className="py-2 pr-4 font-normal">Model</th>
              <th className="py-2 pr-4 text-right font-normal">WER %</th>
              <th className="py-2 pr-4 text-right font-normal">CER %</th>
              <th className="py-2 pr-4 text-right font-normal">Native script %</th>
              <th className="py-2 text-right font-normal">Clips</th>
            </tr>
          </thead>
          <tbody>
            {(['hindi', 'marathi', 'odia', 'kannada'] as Language[]).map((l) =>
              METHOD_ROWS(l).map(([id, label], i) => {
                const r = find(id)
                return (
                  <tr key={id} className={cn('border-b border-line', i === 0 && 'border-t border-line-strong')}>
                    <td className="py-2 pr-4">{i === 0 ? LANGUAGE_NAMES[l].en : ''}</td>
                    <td className="py-2 pr-4">{label}</td>
                    {r ? (
                      <>
                        <td className="num py-2 pr-4 text-right">{r.WER_clean.toFixed(1)}</td>
                        <td className="num py-2 pr-4 text-right">{r.CER_clean.toFixed(1)}</td>
                        <td className="num py-2 pr-4 text-right">{r.script_valid.toFixed(0)}</td>
                        <td className="num py-2 text-right text-muted">{r.n_samples}</td>
                      </>
                    ) : (
                      <td colSpan={4} className="py-2 text-right text-muted">not run yet</td>
                    )}
                  </tr>
                )
              }),
            )}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-muted">whisper-base (74M) + LoRA · 15 h per target · identical decoding · one seed</p>
    </div>
  )
}

/* RQ3: what scoring rules do to the same outputs. */
function ScoringRules({ rows, testSet }: { rows: ResultRow[]; testSet: TestSet }) {
  const shown = rows.filter((r) => r.test_set === testSet && /^(D|H|E|Z|P)-/.test(r.run_id))
  if (!shown.length) return null
  return (
    <div className="mt-10">
      <p className="text-[0.9375rem] text-ink">Same outputs, three scoring rules</p>
      <p className="mt-1 text-xs text-muted">Whisper&apos;s own normalizer deletes Indic vowel signs, so it splits words and changes the score.</p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[30rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[0.6875rem] uppercase tracking-[0.08em] text-muted">
              <th className="py-2 pr-4 font-normal">Run</th>
              <th className="py-2 pr-4 text-right font-normal">raw</th>
              <th className="py-2 pr-4 text-right font-normal">ours</th>
              <th className="py-2 text-right font-normal">Whisper&apos;s</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.run_id} className="border-b border-line">
                <td className="num py-2 pr-4">{r.run_id}</td>
                <td className="num py-2 pr-4 text-right">{r.WER_raw.toFixed(1)}</td>
                <td className="num py-2 pr-4 text-right text-ink">{r.WER_clean.toFixed(1)}</td>
                <td className="num py-2 text-right">{r.WER_whisper_norm.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
