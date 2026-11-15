"""
bench_deploy.py - the deployment trade-off: WER vs size vs speed, on this Mac. Owner: M1.

    python deploy/bench_deploy.py              # every built fine-tuned model, 100 FLEURS clips each

For each model, the same clips go through MLX at fp16 and 4-bit, scored with the
project's contract. The PyTorch-scored WER on those same clips is the reference,
so the table shows what the conversion and the quantization cost.
Run it with nothing else on the GPU: real-time factors are measured, not estimated.
"""
import json
import math
import os
import sys
import time

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "demo"))

from evaluate import score_all  # noqa: E402
from langs import MAX_TOKENS_PER_SEC  # noqa: E402

import store  # noqa: E402

N_CLIPS = 100

# Deployment decoding. Two settings differ from mlx_whisper's defaults, for measured reasons:
#  - without_timestamps: our adapters were trained with <|notimestamps|> in the prompt; the
#    default timestamp mode drops it (Kannada CER 35.6 -> 24.4 on 20 clips when fixed).
#  - Whisper's own loop fallback (re-decode at a higher temperature when the output's compression
#    ratio says it is looping): on marginal clips MLX loops where PyTorch stops.
DECODE = dict(temperature=(0.0, 0.2, 0.4, 0.6), compression_ratio_threshold=2.4,
              condition_on_previous_text=False, without_timestamps=True)
MODELS = ["P-hindi", "H-marathi", "H-kannada", "H-odia"]


def main():
    import mlx_whisper

    manifest = store.models()
    rows = []
    for rid in MODELS:
        if rid not in manifest:
            print("not built:", rid)
            continue
        entry = manifest[rid]
        language = "hindi" if rid == "P-hindi" else rid.split("-", 1)[1]
        token = entry["token"]
        clips = store.clips("fleurs", language)[:N_CLIPS]
        scored = store.raw(rid, "fleurs")
        ref = [c["text"] for c in clips]
        torch_hyp = [scored.loc[c["utt_id"], "hypothesis"] for c in clips]
        torch = score_all(ref, torch_hyp)
        audio = [store.clip_audio("fleurs", language, c["utt_id"])[0] for c in clips]
        seconds = sum(len(a) for a in audio) / 16000

        for precision in ["fp16", "q4"]:
            path = os.path.join(ROOT, entry[precision]["path"])
            mlx_whisper.transcribe(audio[0][:16000], path_or_hf_repo=path, language=token)  # load + warm up
            hyps, t0 = [], time.perf_counter()
            for a in audio:
                cap = min(440, 10 + math.ceil(1.5 * MAX_TOKENS_PER_SEC[language] * len(a) / 16000))
                out = mlx_whisper.transcribe(a, path_or_hf_repo=path, language=token, **DECODE, sample_len=cap)
                hyps.append(out["text"].strip())
            elapsed = time.perf_counter() - t0
            s = score_all(ref, hyps)
            row = {"run_id": rid, "language": language, "precision": precision,
                   "model_mb": entry[precision]["mb"], "clips": len(clips),
                   "audio_s": round(seconds, 1), "rtf": round(elapsed / seconds, 3),
                   "WER": s["WER"], "CER": s["CER"],
                   "WER_pytorch_same_clips": torch["WER"], "CER_pytorch_same_clips": torch["CER"]}
            rows.append(row)
            print(json.dumps(row))

    os.makedirs(os.path.join(ROOT, "results", "tables"), exist_ok=True)
    out = os.path.join(ROOT, "results", "tables", "deployment.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print("wrote", out)


if __name__ == "__main__":
    main()
