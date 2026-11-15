import type { Lane, Language } from '@/lib/api'
import { LANGUAGE_NAMES } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Transcript } from './Transcript'

const fmt = (v: number | null | undefined) => (v == null ? '–' : v.toFixed(0))

/* Phones: each row stacks, the model and its WER / CER on one line, the transcript full width below. */
const STACK = 'max-sm:grid max-sm:grid-cols-[minmax(0,1fr)_auto_auto] max-sm:gap-x-3'

/**
 * One clip, every method, one row each: the reference first, then each model's words with its
 * errors marked and its WER / CER on this clip at the right edge. Rows not run yet say so.
 */
export function LaneTable({
  reference,
  lanes,
  language,
  ignite = false,
  orbWords = false,
  extra,
}: {
  reference: string
  lanes: Lane[]
  language: Language
  ignite?: boolean
  orbWords?: boolean
  extra?: React.ReactNode
}) {
  const lang = LANGUAGE_NAMES[language].lang
  return (
    <table className="w-full table-fixed border-collapse text-left">
      <thead className="max-sm:hidden">
        <tr className="text-[0.6875rem] uppercase tracking-[0.08em] text-muted">
          <th className="w-[10rem] pb-2 pr-3 font-normal">Model</th>
          <th className="pb-2 pr-3 font-normal">Transcript</th>
          <th className="w-14 pb-2 text-right font-normal">WER</th>
          <th className="w-14 pb-2 text-right font-normal">CER</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-line border-t border-line">
        <tr className={STACK}>
          <th scope="row" className="py-2.5 pr-3 align-top text-sm font-medium text-muted max-sm:pb-0">Reference</th>
          <td className="py-2.5 pr-3 max-sm:col-span-3 max-sm:row-start-2 max-sm:pt-1" colSpan={3}>
            <Transcript text={reference} orbWords={orbWords} lang={lang} className="text-[1.0625rem] text-ink" />
          </td>
        </tr>
        {lanes.map((l) => (
          <tr key={l.run_id} className={STACK}>
            <th scope="row" className="py-2.5 pr-3 align-top text-sm font-medium max-sm:pb-0">
              <span className="flex items-center gap-2">
                <MethodSwatch pivot={l.pivot} method={l.method} />
                {l.label}
              </span>
            </th>
            {l.status === 'scored' ? (
              <>
                <td className="py-2.5 pr-3 max-sm:col-span-3 max-sm:row-start-2 max-sm:pt-1">
                  {l.hypothesis ? (
                    <Transcript ops={l.ops} ignite={ignite} orbWords={orbWords} lang={lang} className="text-[1.0625rem]" />
                  ) : (
                    <span className="text-sm text-muted">Empty output</span>
                  )}
                </td>
                <td className="num py-2.5 text-right align-top text-sm max-sm:col-start-2 max-sm:row-start-1 max-sm:pb-0">
                  <span className="text-muted sm:hidden">WER </span>{fmt(l.wer)}
                </td>
                <td className="num py-2.5 text-right align-top text-sm max-sm:col-start-3 max-sm:row-start-1 max-sm:pb-0">
                  <span className="text-muted sm:hidden">CER </span>{fmt(l.cer)}
                </td>
              </>
            ) : (
              <td colSpan={3} className="py-2.5 text-sm text-muted max-sm:col-span-3 max-sm:row-start-2 max-sm:pt-1">
                Not run yet <span className="num text-xs">({l.run_id})</span>
              </td>
            )}
          </tr>
        ))}
        {extra}
      </tbody>
    </table>
  )
}

/** Pivot identity matches the results chart: gold for Hindi, blue for English; outline for none. */
export function MethodSwatch({ pivot, method, className }: { pivot: string; method: string; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-block h-2 w-2 shrink-0 rounded-full',
        pivot === 'hindi' ? 'bg-pivot-hi' : pivot === 'english' ? 'bg-pivot-en' : method === 'zeroshot' ? 'border border-muted' : 'bg-muted',
        className,
      )}
    />
  )
}
