# IndicBridge — 3-day build plan (single M4 MacBook)

**Start:** Mon 2 Nov 2026 · **Finish:** Wed 4 Nov 2026 (evening)
**Machine:** Apple M4 (10-core GPU), 16 GB unified memory. Everything runs here; the same code also runs unchanged on a CUDA box (Kaggle) if we fall behind.

---

## 1. What changed from the Review 1 design, and why

| Change | Why |
|---|---|
| **English added as a second pivot** (LibriSpeech clean-100, 45 h, same steps as the Hindi pivot) | With only a Hindi pivot, a smaller Kannada gain could just mean "Kannada is harder". An English pivot gives every target a matched control: same hours, same steps, an extra training stage, but **no relationship to any target**. `Hindi gain − English gain` is the Hindi-specific benefit, computed per target. |
| **Test set 2 = Kathbath `valid`** (was Common Voice) | Mozilla moved Common Voice to Mozilla Data Collective in Oct 2025. `mozilla-foundation/common_voice_17_0` on HF now holds only a README. Kathbath (AI4Bharat) is read speech from a different source and different speakers than IndicVoices, and covers all four languages. We never train on it. |
| **One GPU instead of four Kaggle accounts** | Runs go one after another through a resumable queue. Step counts are set from a measured throughput benchmark (§5), not guessed. |
| **whisper-base (74M) instead of whisper-small (244M)** | Measured on this M4: whisper-small LoRA trains at 1.35 clips/s at best, so the full grid would take ~99 h. whisper-base trains at 4.54 clips/s, so the full grid fits in ~15 h. The research question is comparative (gain vs gain), so the smaller model answers it equally well. Absolute WER will be higher, and we say so. |
| **Test references must fit Whisper's decoder (≤ 440 tokens)** | Whisper spends ~3 tokens per Odia letter, and 23% of Odia FLEURS test utterances are longer than the decoder can output, for any model. The same rule applies to every language and method, and the excluded share is reported (Odia 23.1%, Kannada 1.3%, Hindi and Marathi 0%). |

### Why the three targets now separate family from script

| Target | Family vs Hindi | Script vs Hindi | What `Gain(Hindi) − Gain(English)` tells us |
|---|---|---|---|
| Marathi | same (Indo-Aryan) | same (Devanagari) | family **plus** script benefit |
| Odia | same (Indo-Aryan) | different | family benefit without shared script |
| Kannada | different (Dravidian) | different | Indian-region (areal) benefit only |

Reading the results:
- Marathi > Odia > Kannada ≈ 0: genealogical relatedness matters.
- Marathi ≫ Odia ≈ Kannada: it is mostly **script**, not family.
- All three ≈ 0: the reference paper's gain is "extra data / extra stage", not relatedness.
- All three > 0 and similar: an Indian-region acoustic benefit (shared retroflex and aspirated sounds) that does not depend on family.

**Caveats to state in the viva:** Whisper is already very strong in English, so the English stage moves the weights less, and LibriSpeech audiobooks are a different recording domain from IndicVoices. We measure how much each pivot stage changed the model (loss drop and LoRA update norm) and report it.

---

## 2. Defects in Build Manual v2 that would each cost a day (all fixed in this repo)

| # | Where | Problem | Fix |
|---|---|---|---|
| 1 | `data_prep.py` | The IndicVoices audio column is `audio_filepath`, not `audio`. Each language is 36–59 GB, and `load_dataset(..., split="train")` downloads all of it. | Read a seeded sample of parquet shards spread across the shard range. Filter on the `duration` column without decoding audio, and keep the original audio bytes. |
| 2 | `cap_hours` | Takes the first N clips (one district or speaker cluster) and decodes every clip just to measure its length. | Seeded shuffle, at most 30 clips per speaker, budget from metadata. |
| 3 | `load_common_voice` | The dataset is no longer on HF. | Kathbath `valid`. |
| 4 | Decoding | `repetition_penalty=1.2` + `no_repeat_ngram_size=4` on byte-level BPE. Odia (and partly Kannada) letters split into several byte tokens that repeat constantly, so these settings **block correct output in exactly the languages we compare**. | Plain greedy decoding, no penalties, identical for every run. |
| 5 | Decoding | `max_new_tokens=200` truncates Odia, which needs several tokens per letter, and the truncation is counted as deletions. | 440 (Whisper's decoder limit is 448 including the 4 prompt tokens). |
| 6 | Training | Labels longer than 448 tokens crash Whisper's decoder. | Filter by label token length in data prep, for every language, **before** capping hours. Report how many clips each language drops. |
| 7 | Training | `ds.map(prepare)` caches a ~1 MB log-mel per clip (~20 GB for the Hindi pivot). | Compute features on the fly in the collator. |
| 8 | Training | Reentrant gradient checkpointing with a frozen base gives LoRA layers inside checkpointed blocks no gradient. | `use_reentrant=False`. |
| 9 | Setup | `pip install --upgrade` on unpinned libraries: `datasets>=4` decodes audio through torchcodec, and newer `transformers` deprecates `forced_decoder_ids` and `tokenizer=`. | Pinned `requirements.txt`. Generate with `language=` / `task=`. |
| 10 | Scoring (RQ3) | Whisper's own `BasicTextNormalizer` turns every Unicode *Mark* character (Indic vowel signs, virama, anusvara) into a space, which shatters words. | Never score with it, but **report WER under it as a third column**. It is a free and striking RQ3 result. |

---

## 3. Experiment grid

Training data rules, the same for every language: IndicVoices `text` column (standard spelling, matches FLEURS and Kathbath references); rows containing `<unintelligible>` are dropped (4–6% of rows; the audio holds speech the text does not); clips are 2–30 s, because 1–2 s backchannels cost a full 30 s Whisper window each; at most 50 clips per speaker; references ≤ 443 tokens.

Fixed across every target: 15 h of IndicVoices training audio, whisper-base, LoRA r=32 / α=64 on `q_proj`, `v_proj`, lr 1e-3, effective batch 16 (4 × 4 accumulation), pivots 2000 steps and targets 1000, greedy decoding capped at 1.5× each language's fastest real token rate, the same two test sets, normalizer contract v3.

| ID | Run | Starts from | Notes |
|---|---|---|---|
| Z-* | Zero-shot: hi, mr, kn, or×{bn, hi, as} | whisper-small | 6 configs × 2 test sets |
| P-hi | Hindi pivot, 45 h | whisper-small | **Gate:** Hindi WER must fall clearly vs zero-shot before anything builds on it |
| P-en | English pivot, 45 h | whisper-small | Same steps as P-hi |
| D-mr, D-kn, D-or | Direct LoRA | whisper-small | Baseline |
| H-mr, H-kn, H-or | Hindi → target | P-hi adapter | Main experiment |
| E-mr, E-kn, E-or | English → target | P-en adapter | Control |
| X-* | Pivot-only transfer: P-hi and P-en scored on every target's tests | — | Evaluation only, cheap |
| T-or-hi, T-or-as | Odia direct with the `hi` and `as` tokens | whisper-small | **Stretch:** completes RQ2 after fine-tuning |

D/H/E-odia all use `<|bn|>`, **fixed in advance** rather than taken from the zero-shot winner, for two reasons:
1. At zero-shot every token produces 0% Odia script, and CER differs only between 161% and 166%. That is a ranking of equally broken outputs.
2. `<|hi|>` is the token the Hindi pivot trains with. Using it for Odia would give H-odia a decoder prompt the English pivot never saw, and the pivot comparison would stop being fair.

Bengali is Odia's closest relative and is used by neither pivot. RQ2 is answered by the T-odia runs, which fine-tune Odia directly under `<|as|>` and `<|hi|>`, compared against D-odia.

---

## 4. Cheap analyses that make the claim defensible

1. **Paired bootstrap 95% CIs** on every transfer gain, resampling test utterances (1,000 resamples, CPU, minutes). With a single seed this stands in for confidence intervals.
2. **Script-validity rate:** the share of output letters that fall in the target script's Unicode block. It makes "Odia comes out in the wrong script" a number, and is central to RQ2.
3. **Tokenizer fertility:** Whisper tokens per character and per word for each language's references. It explains Odia's difficulty and the 448-token limit.
4. **Normalization delta (RQ3):** raw vs contract-normalized vs Whisper-normalized WER, plus whether the method ranking flips.
5. **Pivot-only transfer (X-*):** how much a pivot helps before seeing any target data.

---

## 5. Compute plan for one M4

Measured with `src/bench.py` (2 Nov). MPS memory is capped at ~9.5 GB so an oversized batch fails fast instead of swapping the Mac.

| Model | Best training setting | Clips/s | Full grid at 4000/2000 steps | Tier B (2000/1000) |
|---|---|---|---|---|
| whisper-small | batch 2, fp32, no checkpointing (9.3 GB) | 1.35 | ~99 h | ~49 h |
| **whisper-base** | **batch 4, fp32, no checkpointing (6.5 GB)** | **4.54** | ~29 h | **~15 h ← chosen** |

**Attention implementation (whisper-base, batch 4):** eager attention reaches **5.64 clips/s**, SDPA 4.74, and fp16 is slower with either (5.23 / 4.31). Every training and evaluation run uses fp32 with eager attention. That puts the grid at ~12 h. Zero-shot rows scored earlier with SDPA are kept in `results/_sdpa_zeroshot/` as a sanity check and re-scored with eager.

bf16 gave no speedup on the M4 (0.94 vs 0.99 clips/s), and gradient checkpointing only saves memory.

**Incidents on Tue 3 Nov, early morning (fixed):**
- **Evaluation batch 16 ran out of memory with eager attention.** Evaluation now uses batch 4 for every run. The zero-shot rows were re-scored that way.
- **The Hindi pivot ran out of memory at the first step, twice.** Only 4.5 GB of the 9.5 GB was tensors; the other 4.9 GB was Apple's MPS graph cache, which compiles one graph per tensor shape. Hindi, Odia and Kannada labels run from about 10 to 443 tokens, where English stays under 73. The fix pads labels to multiples of 64 tokens: seven shapes, padding masked out of the loss. Micro-batches went from 4×4 to 2×8 from P-hindi on; the effective batch is 16 throughout, so the optimisation is the same.
- **The queue used to stop on any failure.** It now records `FAILED`, skips that run's dependents, and carries on. Decoding with per-language length caps runs at a real-time factor of 0.05–0.07, so all ~44 evaluations take ~2–3 h.

The queue runs science-critical work first and stretch work last: Z → P-hi → gate → D-* → H-* → P-en → E-* → X-* → T-*. Each finished run writes a `DONE` marker, so the queue resumes after a crash, sleep or reboot. Keep the Mac on power and run `caffeinate`, and avoid heavy apps while it trains: training shares the 16 GB with everything else.

---

## 6. Timeline

### Day 1 — Mon 2 Nov
- **You:** free ≥30 GB of disk. Accept the IndicVoices and Kathbath terms on HF, then `hf auth login`.
- **Claude:** repo, pinned environment, normalizer contract with self-tests, benchmark → tier, tokenizer fertility, smoke test (30 steps on 64 clips: loss falls, adapter saves and reloads, evaluation runs).
- **Data prep** (network-bound): Hindi 45 h, English 45 h, Marathi/Kannada/Odia 15 h each, FLEURS test and Kathbath valid for all four languages.
- **Zero-shot evaluations**, then start the queue running overnight from P-hi.
- **Team:** each member listens to 10 training clips in their language and records code-switching, noise, and digits vs words.

### Day 2 — Tue 3 Nov
- Morning: **pivot gate.** If Hindi WER did not drop, stop and fix before anything else.
- The queue runs D-* → H-* → P-en → E-*, with automatic evaluation after each run.
- **Team:** report §1–5 (most of it is already in the Review 1 TeX), the dataset-analysis section from the listening notes.

### Day 3 — Wed 4 Nov
- Morning: the last runs finish. `analysis.py` produces the results table, CIs, fertility, script validity and charts.
- **Team:** native-speaker error analysis, 50 wrong outputs per language, direct vs multistage.
- **Claude / M1:** merge the best adapters → MLX 4-bit → WER / size / RTF table → offline Gradio demo.
- Evening: results and discussion, slides, viva rehearsal.

### If behind schedule, cut in this order
T-* → X-* for English → E-odia → drop evaluation sets to 400 utterances → tier B.

---

## 7. Findings

| Finding | Number | Why it matters |
|---|---|---|
| Whisper tokens per character | Hindi 1.29 · Marathi 1.30 · Kannada 1.86 · **Odia 3.06** | Odia is the most expensive script for Whisper to write: ~18 tokens per word. |
| FLEURS test utterances longer than the decoder can output | Hindi 0% · Marathi 0% · Kannada 1.3% · **Odia 23.1%** | A structural ceiling for Odia that no amount of training removes. |
| Whisper's `BasicTextNormalizer` on Hindi | `नमस्ते आप कैसे हैं` → `नमस त आप क स ह` | It drops vowel signs and splits words. On one example pair, WER fell from 57% (correct scoring) to 33% (Whisper's normalizer). RQ3. |
| whisper-base zero-shot on Hindi audio | Output is romanized Latin text (`Likhti hai, Agar...`) | "Supported" languages can still come out in the wrong script, which the script-validity metric captures. |
| Hindi pivot (45 h), Hindi test sets | WER 154.7 → **41.0** (FLEURS), 137.0 → **44.0** (Kathbath); 100% Devanagari | Gate passed. |
| **Hindi pivot gain over direct** (WER points, 95% paired-bootstrap CI; FLEURS / Kathbath) | Marathi **+3.1** (2.1–4.1) / **+3.5** (1.9–5.3) · Odia **+3.1** (2.1–4.1) / **+1.9** (0.7–3.1) · Kannada +1.1 (−0.1–2.2) / +0.8 (−0.5–2.0) | Both Indo-Aryan targets gain reliably on both test sets; the Dravidian one does not. Odia shows it is not only shared script. The English-pivot control decides whether this is relatedness or just more data. |
| **RQ2: Odia's borrowed token after training** | Direct Odia WER (FLEURS / Kathbath): `<|bn|>` 74.5 / 64.9 · `<|as|>` 74.9 / 65.0 · `<|hi|>` 73.8 / 64.6; Hindi-vs-Bengali +0.7 (−0.1–1.6) on FLEURS; all three 100% Odia script | **No reliable difference.** At zero-shot every token gives 0% Odia script; after 15 h of training the token barely matters, and the genealogical ordering does not appear. |
| **Deployment (MLX on the M4, 100 FLEURS clips per model)** | fp16, 144 MB: RTF 0.03–0.06, WER within 2.5 points of PyTorch on the same clips. 4-bit, 42 MB: about +6 WER; **Kannada CER 72%** | Ship fp16. 4-bit is too lossy for whisper-base, catastrophically for Kannada. Matching PyTorch needed `without_timestamps=True` (training prompt) and Whisper's loop fallback. Table: `results/tables/deployment.csv`. |
| **Core answer (all 18 core runs, Tue 3 Nov)** | English pivot over direct: never positive (Kannada −1.3 on FLEURS). Hindi pivot over direct: Marathi +3.1/+3.5, Odia +3.1/+1.9, Kannada +1.1/+0.8 (marginal / none). **Hindi minus English: positive for all three** (Mr +3.0/+4.6, Or +3.1/+2.6, Kn +2.5/+1.9). Interaction (Indo-Aryan vs Kannada Hindi advantage): FLEURS none significant; Kathbath only Marathi − Kannada +2.7 (1.0–4.8). Numbers: `results/tables/gains.csv`, `interaction.csv` (fixed-seed paired bootstrap, 1000 resamples). | **Not data quantity:** equal English hours add nothing. **Relatedness, but regional:** an Indian pivot beats an English one for every target, Dravidian included. A family-specific extra is not consistent across test sets; where it appears (Kathbath) it is Marathi, which also shares Hindi's script. |
| **English pivot control, Marathi** (same 45 h, same stage, unrelated language) | English gain over direct: +0.15 (−0.8–1.2) FLEURS · −1.2 (−3.4–0.9) Kathbath, i.e. none. **Hindi-specific advantage (E − H): +3.0 (2.1–3.9) / +4.6 (3.1–6.4)** | The Marathi gain is not "more data" or "an extra stage": the same hours of English give nothing. It comes from the pivot being related, on both test sets. |
| Hindi pivot scored on the targets, before any target training (FLEURS) | Marathi CER 124.7 → **40.8**, 100% native script · Odia CER 166.3 → 105.8, 0% · Kannada CER 140.1 → 105.6, 0% | Sound transfers across families, but script transfers only where it is shared. The pivot writes Kannada and Odia **phonetically in Devanagari**: Kannada ಮಕ್ಕಳಿಗೆ ಅತ್ಯಂತ… → "मक्कलीगे अत्यंता". "Relatedness" mixes script and sound; the target runs separate them. |

---

## 8. Verification

- `python src/normalize.py` passes its self-test, and `--checksum` matches `CONTRACT.md`.
- Smoke test: loss falls within 30 steps, and the saved adapter reloads to an identical output on a fixed clip.
- Pivot gate: P-hi beats zero-shot Hindi on both test sets.
- Results sanity: every row for a language and test set has the same `n_samples`, and all rows share one `norm_version`.
