# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Same stack as the team's Neralu ("Solaris") app: Vite + React + TypeScript + Tailwind v4, built once and served by a local FastAPI server that runs MLX Whisper inference on Apple Silicon. Everything, fonts included, works with the network off.

## Users

A 4-person 3rd-year B.Tech team (RV University, NLP course) presenting at their project review and individual vivas. A presenter drives the demo on an M4 MacBook, often on a projector, while faculty examiners watch and ask questions. Each member owns one language (Hindi, Marathi, Kannada, Odia) and may demo that language on their own in an individual viva.

## Product Purpose

IndicBridge tests whether multistage (pivot → target) LoRA fine-tuning of Whisper works because the pivot language is related to the target, or simply because it adds data. The demo makes the research result visible and checkable live: it transcribes Indic speech offline on the laptop, runs one clip through several models side by side, and shows the measured results. Success means the panel leaves convinced that the numbers are real, the comparison is fair, and the team understands why each model fails where it fails.

## Positioning

It is a controlled experiment, not a "we fine-tuned Whisper" demo. The same clip goes through zero-shot, direct, Hindi-pivot and English-pivot models with identical decoding and one shared scoring contract, and the word errors are marked against the reference. Odia is a language Whisper has no token for.

## Operating Context

- Live in a viva room: projector, Wi-Fi deliberately turned off to prove offline inference, the presenter speaking or picking test clips while answering questions.
- Models: whisper-base + LoRA adapters merged and converted to MLX (fp16 and 4-bit) under `mlx_models/`; available models are discovered at runtime, because training finishes in stages.
- Test clips with references: FLEURS test and Kathbath valid samples in `data/test_*.parquet`.
- Results: `results/results_master.csv`, `results/raw/*.csv` (per-utterance outputs) and `results/tables/*.csv` from `src/analysis.py`.

## Capabilities and Constraints

- Must show: (1) live offline transcription from the microphone, with real-time factor and model size; (2) one clip, four models side by side, with errors marked against the reference; (3) the research results (transfer gains with bootstrap 95% CIs, the Marathi / Odia / Kannada comparison, normalization effects); (4) the Odia tokenizer story: no `<|or|>` token, wrong-script output, ~3 Whisper tokens per Odia letter, 23% of FLEURS Odia utterances longer than the decoder can output.
- Scoring must use the project's contract (`src/normalize.py`, `src/evaluate.py`) so on-screen WER/CER match the report.
- Terminology: zero-shot, direct (LoRA on the target only), multistage / pivot (Hindi → target, English → target), WER, CER, script validity, real-time factor (RTF).
- Base model is whisper-base (74M), chosen because whisper-small trained at 1.35 clips/s on the M4. Absolute WERs are high; relative gains are the result.
- Results arrive while the demo is being built: every view must handle "not run yet" honestly.

## Brand Commitments

- Name: IndicBridge.
- Visual language (user's request, 4 Nov 2026, replacing the earlier Neralu binding): minimalist, far less text, and it must not resemble the team's Neralu hackathon site (no deep-space starfield, no mint neon). Type is GitHub Next's Monaspace superfamily, self-hosted. The hero background is a 3D perspective tunnel of cards behind the MorphOrb, which stays. Light theme by default (projector), dark theme on request. Colour only where it carries meaning, 1 px lines.
- Neralu's rules carry over: no emoji, no "AI-powered" marketing copy, no placeholder UI (if a button exists it works), anything simulated or example data is labelled.

## Evidence on Hand

Real, measured, in this repo: benchmark numbers (`config.json`), tokenizer fertility and decoder-limit counts (`PLAN.md` §7), zero-shot results, and, as runs finish, every trained result. Nothing may be invented: no fabricated WERs, users or claims. Rows not yet run are shown as not run.

## Product Principles

1. Every number on screen is traceable to a file in `results/` or `data/`.
2. Show where a model is wrong, not just how often.
3. Same conditions for every model, and say so on screen.
4. Offline is a claim the demo proves, not a label.
5. Honest about limits: high absolute WER, single seed, whisper-base.

## Accessibility & Inclusion

Projector-legible: high contrast, large type for transcripts, a light theme toggle. Indic scripts (Devanagari, Kannada, Odia) render with bundled Noto fonts at reading sizes.
