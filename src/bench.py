"""
bench.py - measure how fast this machine trains and decodes, then pick
step counts that let the whole grid finish in the time we have.

    python src/bench.py            # ~5 minutes, writes config.json

Uses synthetic log-mels: Whisper always pads audio to 30 s, so the
encoder cost per clip does not depend on the clip.
"""
import json
import os
import subprocess
import sys
import time

import torch
from peft import LoraConfig, get_peft_model
from transformers import WhisperForConditionalGeneration

from train_lora import pick_device

MODEL = os.environ.get("BENCH_MODEL", "openai/whisper-small")
LABEL_LEN = 120          # a long-ish Indic transcript in Whisper tokens
GPU_HOURS_AVAILABLE = 40 # of the ~72 h wall clock, after data prep, evals and demo

# Training samples per run at effective batch 16
GRID = {"pivot_runs": 2, "target_runs": 9, "stretch_runs": 2}

# Cap MPS memory well below 16 GB so a config that does not fit fails with
# an OOM error instead of pushing the whole Mac into swap.
MPS_CAP = "0.8"
CONFIGS = [(2, "fp32", False), (4, "fp32", True), (8, "fp32", True),
           (8, "bf16", True), (16, "bf16", True)]


def sync(device):
    if device == "mps":
        torch.mps.synchronize()
    elif device == "cuda":
        torch.cuda.synchronize()


def train_rate(device, batch, precision, grad_ckpt, steps=6):
    model = WhisperForConditionalGeneration.from_pretrained(MODEL)
    model.config.use_cache = False
    if grad_ckpt:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model = get_peft_model(model, LoraConfig(r=32, lora_alpha=64,
                                             target_modules=["q_proj", "v_proj"],
                                             lora_dropout=0.05)).to(device)
    model.train()     # HF only applies gradient checkpointing in training mode
    opt = torch.optim.AdamW([q for q in model.parameters() if q.requires_grad], lr=1e-3)
    feats = torch.randn(batch, 80, 3000, device=device)
    labels = torch.randint(0, 50000, (batch, LABEL_LEN), device=device)
    autocast = torch.autocast(device_type=device, dtype=torch.bfloat16,
                              enabled=precision == "bf16")
    for i in range(steps + 2):
        if i == 2:
            sync(device)
            t0 = time.time()
        with autocast:
            loss = model(input_features=feats, labels=labels).loss
        loss.backward()
        opt.step()
        opt.zero_grad()
    sync(device)
    rate = batch * steps / (time.time() - t0)
    mem = torch.mps.driver_allocated_memory() / 1e9 if device == "mps" else float("nan")
    del model, opt
    if device == "mps":
        torch.mps.empty_cache()
    return rate, mem


def decode_rate(device, dtype, batch=16, new_tokens=60):
    model = WhisperForConditionalGeneration.from_pretrained(MODEL)
    model = model.to(device=device, dtype=dtype).eval()
    feats = torch.randn(batch, 80, 3000, device=device, dtype=dtype)
    with torch.no_grad():
        model.generate(feats[:2], language="hindi", max_new_tokens=5)
        sync(device)
        t0 = time.time()
        model.generate(feats, language="hindi", min_new_tokens=new_tokens,
                       max_new_tokens=new_tokens)
        sync(device)
    return batch / (time.time() - t0)


def one(batch, precision, ckpt):
    """Measure one config; runs in its own process so memory is fully freed."""
    row = {"batch": batch, "precision": precision, "grad_ckpt": ckpt}
    try:
        rate, mem = train_rate(pick_device(), batch, precision, ckpt)
        row.update(samples_per_sec=round(rate, 2), mem_gb=round(mem, 1))
    except Exception as e:                          # OOM or unsupported dtype
        row["error"] = f"{type(e).__name__}: {str(e)[:120]}"
    print("RESULT " + json.dumps(row), flush=True)


def main():
    if sys.argv[1:2] == ["--one"]:
        b, prec, ck = sys.argv[2:5]
        return one(int(b), prec, ck == "True")
    device = pick_device()
    print("Device:", device)
    env = {**os.environ, "PYTORCH_MPS_HIGH_WATERMARK_RATIO": MPS_CAP,
           "PYTORCH_MPS_LOW_WATERMARK_RATIO": "0.6"}
    results = []
    for batch, precision, ckpt in CONFIGS:
        out = subprocess.run([sys.executable, __file__, "--one", str(batch), precision,
                              str(ckpt)], env=env, capture_output=True, text=True).stdout
        line = [l for l in out.splitlines() if l.startswith("RESULT ")]
        results.append(json.loads(line[0][7:]) if line else
                       {"batch": batch, "precision": precision, "grad_ckpt": ckpt,
                        "error": "crashed"})
        print(results[-1], flush=True)

    ok = [r for r in results if "samples_per_sec" in r]
    best = max(ok, key=lambda r: r["samples_per_sec"])

    dec = {}
    os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = MPS_CAP
    os.environ["PYTORCH_MPS_LOW_WATERMARK_RATIO"] = "0.6"
    for name, dt in [("fp32", torch.float32), ("fp16", torch.float16)]:
        try:
            dec[name] = round(decode_rate(device, dt), 2)
        except Exception as e:
            dec[name] = f"{type(e).__name__}: {str(e)[:80]}"
        print("decode", name, dec[name], "clips/sec", flush=True)

    # Hours for the grid at each tier
    def grid_hours(pivot_steps, target_steps):
        samples = 16 * (GRID["pivot_runs"] * pivot_steps
                        + (GRID["target_runs"] + GRID["stretch_runs"]) * target_steps)
        return samples / best["samples_per_sec"] / 3600

    tiers = {"A": (4000, 2000), "B": (2000, 1000), "C": (1500, 750)}
    hours = {t: round(grid_hours(*s), 1) for t, s in tiers.items()}
    tier = next((t for t in "ABC" if hours[t] <= GPU_HOURS_AVAILABLE), "C")

    config = {
        "device": device,
        "tier": tier,
        "pivot_steps": tiers[tier][0],
        "target_steps": tiers[tier][1],
        "batch_size": best["batch"],
        "grad_accum": 16 // best["batch"],
        "precision": best["precision"],
        "grad_ckpt": best["grad_ckpt"],
        "eval_dtype": "fp32",
        "eval_batch": 16,
        "bench": {"train": results, "decode_clips_per_sec": dec, "grid_hours": hours},
    }
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
