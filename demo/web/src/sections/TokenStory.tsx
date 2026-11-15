import { useEffect, useState } from 'react'
import { api, LANGUAGE_NAMES, type Language, type LanguageFacts, type ResultRow, type Tokens } from '@/lib/api'

/**
 * Why Odia is the hard case, shown from the tokenizer itself: one real test sentence broken into
 * Whisper's tokens, most of them single bytes, and three measured facts in one line.
 */
export function TokenStory() {
  const [facts, setFacts] = useState<Record<Language, LanguageFacts> | null>(null)
  const [rows, setRows] = useState<ResultRow[]>([])
  const [tokens, setTokens] = useState<Tokens | null>(null)

  useEffect(() => {
    api.facts().then((f) => setFacts(f.languages)).catch(() => undefined)
    api.results().then((r) => setRows(r.rows)).catch(() => undefined)
    api
      .lanes('odia', 'fleurs')
      .then((d) => api.tokens(d.reference))
      .then(setTokens)
      .catch(() => undefined)
  }, [])

  const zeroshot = rows.find((r) => r.run_id === 'Z-odia-bengali' && r.test_set === 'fleurs')
  const odia = facts?.odia
  const hindi = facts?.hindi
  const names = LANGUAGE_NAMES.odia

  return (
    <section id="odia" className="mx-auto max-w-6xl px-5 py-28 sm:px-8 sm:py-36" aria-labelledby="odia-title">
      <h2 id="odia-title" className="display max-w-4xl text-[2.25rem] sm:text-[3.5rem]">
        Whisper has <span className="hand">never seen</span> Odia.
      </h2>

      {tokens ? (
        <figure className="mt-14">
          <p className="script max-w-4xl text-[1.5rem] leading-[1.6] sm:text-[1.875rem]" lang={names.lang}>
            {tokens.text}
          </p>
          <ol className="mt-8 flex flex-wrap gap-1" aria-label={`Whisper's ${tokens.tokens.length} tokens for this sentence`}>
            {tokens.tokens.map((t, i) => (
              <li
                key={i}
                title={t.text ? `"${t.text}" · bytes ${t.hex}` : `Part of a letter · byte ${t.hex}`}
                className={
                  t.text
                    ? 'script rounded-[5px] border border-line-strong bg-surface px-1.5 text-[0.8125rem] leading-6'
                    : 'num rounded-[5px] bg-sunken px-1 text-[0.6875rem] leading-6 text-muted'
                }
                lang={t.text ? names.lang : undefined}
              >
                {t.text ? chipLabel(t.text) : t.hex}
              </li>
            ))}
          </ol>
          <figcaption className="hand mt-4 text-[0.9375rem] text-muted">
            {tokens.tokens.length} tokens for {tokens.letters} letters. Grey ones are single bytes, pieces of one letter.
          </figcaption>
        </figure>
      ) : (
        <p className="mt-14 text-sm text-muted">Loading a test sentence…</p>
      )}

      {odia && (
        <ul className="mt-14 flex flex-wrap gap-x-10 gap-y-3 border-t border-line pt-6 text-[0.9375rem] text-muted">
          {odia.tokens_per_letter != null && (
            <li>
              <span className="num text-ink">{odia.tokens_per_letter.toFixed(2)}</span> tokens per letter
              {hindi?.tokens_per_letter != null && <> (Hindi <span className="num">{hindi.tokens_per_letter.toFixed(2)}</span>)</>}
            </li>
          )}
          {odia.too_long_pct != null && (
            <li>
              <span className="num text-ink">{odia.too_long_pct.toFixed(0)}%</span> of sentences too long for the decoder
            </li>
          )}
          {zeroshot && (
            <li>
              <span className="num text-ink">{zeroshot.script_valid.toFixed(0)}%</span> Odia script before training
            </li>
          )}
        </ul>
      )}
    </section>
  )
}

/** What a text chip shows: spaces as ␣, zero-width joiners by name, a lone vowel sign on a dotted circle. */
const ZERO_WIDTH: Record<string, string> = { '\u200b': 'ZWSP', '\u200c': 'ZWNJ', '\u200d': 'ZWJ', '\ufeff': 'BOM' }
function chipLabel(text: string) {
  if (!text.trim()) return '␣'
  const chars = [...text]
  if (chars.every((c) => c in ZERO_WIDTH)) return chars.map((c) => ZERO_WIDTH[c]).join(' ')
  const visible = chars.filter((c) => !(c in ZERO_WIDTH)).join('')
  return /^\p{M}/u.test(visible) ? `\u25cc${visible}` : visible
}
