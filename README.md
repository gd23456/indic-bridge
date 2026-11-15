# IndicBridge

Cross-lingual multistage LoRA fine-tuning of Whisper (base, 74M; see PLAN.md §5 for why not small) for Hindi, Marathi, Kannada and Odia.
The question: does a pivot language help **because it is related** to the target, or just because it adds data?

- **Plan, design changes and the defects fixed from Build Manual v2:** [PLAN.md](PLAN.md)
- **Shared-file ownership and checksum:** [CONTRACT.md](CONTRACT.md)

## Setup (macOS, Apple Silicon)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # pinned; never `pip install --upgrade`
hf auth login                            # then accept the terms on the HF pages of
                                         # ai4bharat/IndicVoices and ai4bharat/Kathbath
python src/normalize.py                  # self-test + checksum (must match CONTRACT.md)
```

## Pipeline

```bash
python src/bench.py                                  # measures this machine, writes config.json

# data (≈15 GB downloaded, ≈9 GB kept)
python src/data_prep.py train --language hindi   --hours 45
python src/data_prep.py train --language english --hours 45 --max_per_speaker 120
for L in marathi kannada odia; do python src/data_prep.py train --language $L --hours 15; done
for L in hindi marathi kannada odia; do python src/data_prep.py test --language $L; done

# every experiment, resumable, keeps the Mac awake
caffeinate -dimsu python src/run_queue.py
python src/run_queue.py --dry                         # what is done, ready, blocked

python src/analysis.py                                # tables in results/tables/
```

## Offline demo (for the viva)

```bash
pip install -r requirements-demo.txt                 # MLX, FastAPI (Apple Silicon only)
python deploy/build_models.py                         # zero-shot + every finished run -> mlx_models/ (fp16 and 4-bit)
cd demo/web && npm install && npm run build && cd ../..
python demo/server.py                                 # open http://127.0.0.1:8000, then turn Wi-Fi off
```

The page reads only `data/`, `results/` and `mlx_models/`; nothing leaves the Mac. Re-run
`build_models.py` as runs finish and the demo picks the new models up on refresh. Dev mode with hot
reload: `npm run dev` in `demo/web` (proxies `/api` to the server).

## Layout

| Path | What |
|---|---|
| `src/normalize.py`, `src/evaluate.py` | scoring contract: NFC, danda, digits, tags; WER/CER raw, clean and Whisper-normalized; script validity |
| `src/data_prep.py` | seeded, speaker-capped sampling from IndicVoices / LibriSpeech; FLEURS test and Kathbath valid as test sets |
| `src/train_lora.py` | one training loop for direct and multistage runs (MPS or CUDA), resumable |
| `src/eval_model.py` | zero-shot and adapter evaluation with identical greedy decoding |
| `src/experiments.py`, `src/run_queue.py` | the grid and the runner |
| `src/analysis.py` | gains with paired bootstrap CIs, interaction, normalization, fertility |
| `deploy/build_models.py` | merge LoRA → MLX fp16 / 4-bit, writes `mlx_models/manifest.json` |
| `demo/server.py`, `demo/store.py` | local API: clips, scored outputs with word alignment, live MLX transcription, results with bootstrap CIs |
| `demo/web/` | the demo UI (Vite + React + Tailwind v4, shadcn layout); the orb is `src/components/ui/ai-thiking-orb-and-input.tsx` |
| `results/` | `results_master.csv`, per-utterance outputs in `raw/`, tables |
