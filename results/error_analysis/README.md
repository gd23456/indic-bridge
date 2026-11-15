# Native-speaker error analysis: how to fill in your language

One file per language: `hindi_50.csv`, `marathi_50.csv`, `kannada_50.csv`, `odia_50.csv`.
Each has **50 FLEURS test clips** where at least one of the two models made a word error, picked
with a fixed seed (reproducible, not hand-picked). The audio for each row is in
`<language>_audio/<clip>` (e.g. `odia_audio/07.wav`).

| Column | Meaning |
|---|---|
| `runs` | Which two models are compared: `D-<lang> vs H-<lang>` (direct vs Hindi-pivot). Hindi: `Z-hindi vs P-hindi` (zero-shot vs fine-tuned). |
| `reference` | What was actually said (FLEURS transcript). |
| `direct`, `multistage` | The two models' outputs (for Hindi: zero-shot, fine-tuned). |
| `direct_word_err`, `multistage_word_err` | Word errors on this clip (after normalization). |
| `direct_errors`, `multistage_errors` | **You fill these in**: one or more categories below, separated by `\|`. |
| `notes` | **You fill this in**: one line in English on what went wrong and why, as a native speaker. |

## Categories

| Code | Use when | Example |
|---|---|---|
| `SCRIPT` | Wrong writing system | Odia audio written in Devanagari |
| `PHONETIC` | A similar-sounding word or letter | aspirated vs unaspirated (क / ख), short vs long vowel |
| `MORPHOLOGY` | Right root, wrong ending | wrong case marker or tense suffix |
| `SEGMENTATION` | Words wrongly joined or split | a compound written as two words |
| `CODE_SWITCH` | An English word in the speech, written wrongly | "office" in Latin vs native script |
| `NUMBER` | Digits vs words | "two thousand" vs "2000" |
| `HALLUCINATION` | Invented or repeated text | "qaqaqa…", a phrase looping |
| `REFERENCE_WRONG` | The FLEURS reference itself is wrong | count these; it is a finding |

**Steps (about 1–2 hours):** open the CSV in Excel or Google Sheets. It's UTF-8 with a byte-order
mark, so Indic text displays correctly. Play each clip, compare the two outputs with the
reference, fill both `_errors` columns and `notes`, and save as CSV under the same name.

**What we're looking for:** which error types the Hindi pivot *removes*, compared with the
direct model, and which it doesn't. Our prediction: it fixes `PHONETIC` errors (Indian sounds)
more than `MORPHOLOGY` (grammar specific to your language). Your counts decide whether that holds.
