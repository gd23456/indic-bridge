import { Fragment } from 'react'
import type { Op } from '@/lib/api'
import { cn } from '@/lib/utils'

/**
 * A model's words, marked against the reference: wrong words red (substituted solid, inserted
 * dashed), dropped words as struck ghosts of the reference. `ignite` lights the errors once, in
 * order. `orbWords` wraps each word for the orb card's word-by-word reveal.
 */
export function Transcript({
  ops,
  text,
  ignite = false,
  orbWords = false,
  className,
  lang,
}: {
  ops?: Op[]
  text?: string
  ignite?: boolean
  orbWords?: boolean
  className?: string
  lang?: string
}) {
  let errorIndex = 0
  const word = (w: string, kind: 'ok' | 'sub' | 'ins' | 'del', key: string, title?: string) => {
    const i = kind === 'ok' ? 0 : errorIndex++
    return (
      <Fragment key={key}>
        <span className={orbWords ? 'mo-w' : undefined}>
          <span className={`mk-${kind}`} style={kind === 'ok' ? undefined : ({ '--i': i } as React.CSSProperties)} title={title}>
            {w}
          </span>
        </span>{' '}
      </Fragment>
    )
  }

  if (!ops) {
    return (
      <p className={cn('script', className)} lang={lang}>
        {(text ?? '').split(/\s+/).filter(Boolean).map((w, i) => word(w, 'ok', String(i)))}
      </p>
    )
  }

  const out: React.ReactNode[] = []
  ops.forEach((op, j) => {
    if (op.type === 'equal') op.hyp.forEach((w, k) => out.push(word(w, 'ok', `${j}-${k}`)))
    else if (op.type === 'substitute') op.hyp.forEach((w, k) => out.push(word(w, 'sub', `${j}-${k}`, `Reference: ${op.ref.join(' ')}`)))
    else if (op.type === 'insert') op.hyp.forEach((w, k) => out.push(word(w, 'ins', `${j}-${k}`, 'Not in the reference')))
    else op.ref.forEach((w, k) => out.push(word(w, 'del', `${j}-${k}`, 'Dropped: in the reference, not in the output')))
  })
  return (
    <p className={cn('script', ignite && 'ignite', className)} lang={lang}>
      {out}
    </p>
  )
}

/** The three marks, explained once wherever transcripts are compared. */
export function MarkKey({ className }: { className?: string }) {
  return (
    <p className={cn('flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted', className)}>
      <span><span className="mk-sub">word</span> wrong word</span>
      <span><span className="mk-ins">word</span> extra word</span>
      <span><span className="mk-del">word</span> dropped word</span>
    </p>
  )
}
