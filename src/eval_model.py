"""
eval_model.py - score plain Whisper (zero-shot) or Whisper + a LoRA adapter
on one test set. Owner: M4.

Zero-shot and trained models go through the same inference loop and the
same decoding settings, so they are scored identically.

    python src/eval_model.py --run_id Z-odia-bengali --test data/test_fleurs_odia.parquet \
        --language bengali --target_lang odia --method zeroshot
    python src/eval_model.py --run_id H-odia --test data/test_fleurs_odia.parquet \
        --adapter runs/H-odia/adapter --language bengali --target_lang odia \
        --method multistage_lora --pivot hindi
"""
import argparse
import json
import math
import os
import time

import pyarrow.parquet as pq
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from audio import decode
from evaluate import save_raw, save_result, score_run
from langs import MAX_TOKENS_PER_SEC
from train_lora import pick_device

# Identical for every run. No repetition_penalty / no_repeat_ngram_size:
# Odia and Kannada letters are several byte-level tokens each, and those
# settings forbid exactly the repeats these scripts need.
DECODING = {"num_beams": 1, "do_sample": False}
MAX_NEW_TOKENS = 440        # Whisper's decoder holds 448 including the prompt


def token_cap(seconds, target_lang):
    """Same rule for every run of a language: 1.5x its fastest real token rate."""
    return min(MAX_NEW_TOKENS, 10 + math.ceil(1.5 * MAX_TOKENS_PER_SEC[target_lang] * seconds))


def load_model(base_model, adapter, device, dtype):
    # Same attention code as training (see train_lora.build_model)
    model = WhisperForConditionalGeneration.from_pretrained(
        base_model, attn_implementation="eager")
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
    model.config.use_cache = True
    return model.to(device=device, dtype=dtype).eval()


def transcribe(model, processor, arrays, language, device, dtype, batch_size, target_lang):
    """Shared inference loop. Batches clips of similar length together."""
    order = sorted(range(len(arrays)), key=lambda i: len(arrays[i]))
    hyps = [None] * len(arrays)
    for start in range(0, len(order), batch_size):
        idx = order[start:start + batch_size]
        feats = processor.feature_extractor(
            [arrays[i] for i in idx], sampling_rate=16000,
            return_tensors="pt").input_features.to(device=device, dtype=dtype)
        with torch.no_grad():
            cap = token_cap(len(arrays[idx[-1]]) / 16000, target_lang)
            ids = model.generate(feats, language=language, task="transcribe",
                                 max_new_tokens=cap, **DECODING)
        for i, text in zip(idx, processor.batch_decode(ids, skip_special_tokens=True)):
            hyps[i] = text.strip()
        if start % (batch_size * 10) == 0:
            print(f"  {start}/{len(arrays)}  HYP: {hyps[idx[-1]][:80]}", flush=True)
    return hyps


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run_id",      required=True)
    p.add_argument("--test",        required=True, help="data/test_<set>_<lang>.parquet")
    p.add_argument("--adapter",     default=None)
    p.add_argument("--base_model",  default="openai/whisper-base")
    p.add_argument("--language",    required=True, help="Whisper language NAME")
    p.add_argument("--target_lang", required=True, help="our label: odia etc")
    p.add_argument("--method",      required=True,
                   help="zeroshot | direct_lora | multistage_lora | pivot | pivot_transfer")
    p.add_argument("--pivot",       default="none")
    p.add_argument("--train_hours", type=float, default=0.0)
    p.add_argument("--train_steps", type=int, default=0)
    p.add_argument("--batch_size",  type=int, default=16)
    p.add_argument("--dtype",       choices=["fp32", "fp16"], default="fp32")
    p.add_argument("--max_utts",    type=int, default=None, help="smoke tests only")
    args = p.parse_args()

    device = pick_device()
    dtype = torch.float16 if args.dtype == "fp16" else torch.float32
    processor = WhisperProcessor.from_pretrained(args.base_model)
    model = load_model(args.base_model, args.adapter, device, dtype)

    table = pq.read_table(args.test, columns=["utt_id", "text", "audio"]).to_pydict()
    n = args.max_utts or len(table["text"])
    refs, utt_ids = table["text"][:n], table["utt_id"][:n]
    arrays = [decode(b) for b in table["audio"][:n]]
    print(f"Scoring {n} clips from {args.test} with <|{args.language}|>")

    t0 = time.time()
    hyps = transcribe(model, processor, arrays, args.language, device, dtype,
                      args.batch_size, args.target_lang)
    secs = time.time() - t0

    scores = score_run(refs, hyps, args.target_lang)
    scores["rtf"] = round(secs / (sum(len(a) for a in arrays) / 16000), 4)
    print(json.dumps(scores, indent=2))

    test_set = os.path.basename(args.test).split("_")[1]       # fleurs | kathbath
    save_raw(utt_ids, refs, hyps, f"{args.run_id}__{test_set}")
    if args.max_utts:
        print("Smoke test: not writing to results_master.csv")
        return
    save_result({
        "run_id":      args.run_id,
        "language":    args.target_lang,
        "method":      args.method,
        "pivot":       args.pivot,
        "lang_token":  args.language,
        "base_model":  args.base_model + (f"+{args.adapter}" if args.adapter else ""),
        "train_hours": args.train_hours,
        "train_steps": args.train_steps,
        "test_set":    test_set,
        **{k: v for k, v in scores.items() if k != "rtf"},
    })


if __name__ == "__main__":
    main()
