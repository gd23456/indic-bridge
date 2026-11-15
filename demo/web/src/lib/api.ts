/** Typed calls to demo/server.py. Every number the page shows arrives through here. */

export type Language = 'hindi' | 'marathi' | 'kannada' | 'odia'
export type TestSet = 'fleurs' | 'kathbath'

export interface ModelEntry {
  language: string
  method: string
  pivot: string
  token: string
  base: string
  fp16: { path: string; mb: number }
  q4: { path: string; mb: number }
}

export interface Status {
  online: boolean
  models: Record<string, ModelEntry>
  languages: Language[]
  test_sets: TestSet[]
  results: number
}

export interface Clip {
  utt_id: string
  index: number
  duration: number
  text: string
}

export interface Op {
  type: 'equal' | 'substitute' | 'delete' | 'insert'
  ref: string[]
  hyp: string[]
}

export interface Lane {
  run_id: string
  method: string
  label: string
  pivot: string
  status: 'scored' | 'not_run'
  hypothesis?: string
  script_valid?: number
  ops?: Op[]
  wer?: number | null
  cer?: number | null
}

export interface Lanes {
  utt_id: string
  test_set: TestSet
  language: Language
  reference: string
  lanes: Lane[]
}

export interface Transcription {
  text: string
  seconds: number
  elapsed: number
  rtf: number
  model_mb: number
  precision: 'fp16' | 'q4'
  online: boolean
  script_valid?: number
  reference?: string
  ops?: Op[]
  wer?: number | null
  cer?: number | null
}

export interface ResultRow {
  run_id: string
  language: string
  method: string
  pivot: string
  lang_token: string
  test_set: TestSet
  WER_raw: number
  WER_clean: number
  CER_raw: number
  CER_clean: number
  WER_whisper_norm: number
  script_valid: number
  n_samples: number
}

export interface Gain {
  language: Language
  test_set: TestSet
  metric: 'WER' | 'CER'
  gain: 'hindi_pivot' | 'english_pivot' | 'hindi_specific'
  points: number | null
  ci_low?: number
  ci_high?: number
}

export interface Results {
  rows: ResultRow[]
  gains: Gain[]
  odia_tokens: ResultRow[]
}

export interface LanguageFacts {
  too_long_pct: number | null
  too_long: number | null
  split_clips: number | null
  tokens_per_letter?: number
  tokens_per_word?: number
}

export interface Tokens {
  text: string
  tokens: { hex: string; text: string | null }[]
  letters: number
  per_letter: number
}

/** An error a presenter can act on: what failed, and what to do about it. */
async function failure(r: Response) {
  const detail = (await r.json().catch(() => null))?.detail
  if (detail) return new Error(String(detail))
  if (r.status >= 500) return new Error('The demo server failed on this request. Try again; if it repeats, see runs/demo_server.log or restart it with python demo/server.py.')
  return new Error(`The demo server refused this request (${r.status}).`)
}

async function get<T>(path: string): Promise<T> {
  let r: Response
  try {
    r = await fetch(path)
  } catch {
    throw new Error('The demo server is not reachable. Start it with python demo/server.py.')
  }
  if (!r.ok) throw await failure(r)
  return r.json() as Promise<T>
}

const qs = (o: Record<string, string | undefined>) =>
  new URLSearchParams(Object.entries(o).filter((e): e is [string, string] => !!e[1])).toString()

export const api = {
  status: () => get<Status>('/api/status'),
  clips: (language: Language, test_set: TestSet) => get<{ clips: Clip[] }>(`/api/clips?${qs({ language, test_set })}`),
  lanes: (language: Language, test_set: TestSet, utt_id?: string) => get<Lanes>(`/api/lanes?${qs({ language, test_set, utt_id })}`),
  audioUrl: (language: Language, test_set: TestSet, utt_id: string) => `/api/audio?${qs({ language, test_set, utt_id })}`,
  results: () => get<Results>('/api/results'),
  facts: () => get<{ languages: Record<Language, LanguageFacts> }>('/api/facts'),
  tokens: (text: string) => get<Tokens>(`/api/tokens?${qs({ text })}`),
  async transcribe(form: {
    model: string
    language: Language
    token: string
    precision?: 'fp16' | 'q4'
    test_set?: TestSet
    utt_id?: string
    file?: Blob
  }): Promise<Transcription> {
    const body = new FormData()
    for (const [k, v] of Object.entries(form)) {
      if (v === undefined) continue
      if (v instanceof Blob) body.append(k, v, 'speech.wav')
      else body.append(k, String(v))
    }
    let r: Response
    try {
      r = await fetch('/api/transcribe', { method: 'POST', body })
    } catch {
      throw new Error('The demo server is not reachable. Start it with python demo/server.py.')
    }
    if (!r.ok) throw await failure(r)
    return r.json()
  },
}

export const LANGUAGE_NAMES: Record<Language, { en: string; native: string; lang: string }> = {
  hindi: { en: 'Hindi', native: 'हिन्दी', lang: 'hi' },
  marathi: { en: 'Marathi', native: 'मराठी', lang: 'mr' },
  kannada: { en: 'Kannada', native: 'ಕನ್ನಡ', lang: 'kn' },
  odia: { en: 'Odia', native: 'ଓଡ଼ିଆ', lang: 'or' },
}

/** The best model built for a language: Hindi-pivot, then direct, then zero-shot. */
export function bestModel(models: Record<string, ModelEntry>, language: Language) {
  const order = language === 'hindi' ? ['P-hindi'] : [`H-${language}`, `D-${language}`, `E-${language}`]
  for (const id of order) if (models[id]) return { id, entry: models[id] }
  if (models.zeroshot) return { id: 'zeroshot', entry: models.zeroshot }
  return null
}

/** Whisper has no Odia token; every Odia run borrows Bengali's (fixed in advance, see PLAN.md). */
export const whisperToken = (language: Language) => (language === 'odia' ? 'bengali' : language)

export const METHOD_LABEL: Record<string, string> = {
  zeroshot: 'Zero-shot',
  direct_lora: 'Direct',
  multistage_lora: 'Multistage',
  pivot: 'Hindi pivot',
}
