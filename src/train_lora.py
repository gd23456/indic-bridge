"""
train_lora.py - one script for ALL training runs. Owner: M1.

Direct:
    python src/train_lora.py --data data/train_odia_15h.parquet --language bengali \
        --out runs/D-odia --max_steps 2000

Multistage (stage 2, starting from the Hindi pivot) - the only difference
is --init_adapter:
    python src/train_lora.py --data data/train_odia_15h.parquet --language bengali \
        --init_adapter runs/P-hindi/adapter --out runs/H-odia --max_steps 2000

A plain PyTorch loop rather than Seq2SeqTrainer: it runs the same on
Apple MPS and CUDA, and every line of the method is visible for the viva.
Restarting the same command resumes from the last checkpoint.
"""
import argparse
import json
import math
import os
import random
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import pyarrow.parquet as pq
import torch
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import (WhisperForConditionalGeneration, WhisperProcessor,
                          get_linear_schedule_with_warmup)

from audio import decode


def pick_device():
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class ParquetSpeech(torch.utils.data.Dataset):
    """
    Reads clips lazily from a data_prep.py parquet file.
    The table is opened inside each DataLoader worker, so tens of GB of
    audio are never pickled between processes.
    """

    def __init__(self, path):
        self.path = path
        self.texts = pq.read_table(path, columns=["text"]).column("text").to_pylist()
        self._audio = None

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, i):
        if self._audio is None:
            self._audio = pq.read_table(self.path, columns=["audio"],
                                        memory_map=True).column("audio")
        return {"array": decode(self._audio[i].as_py()), "text": self.texts[i]}


@dataclass
class Collator:
    """
    Log-mel features are computed here, inside the DataLoader workers,
    instead of being cached to disk (~1 MB per clip) up front.
    """
    processor: Any

    def __call__(self, items):
        feats = self.processor.feature_extractor(
            [x["array"] for x in items], sampling_rate=16000,
            return_tensors="pt").input_features

        # Pad to a multiple of 64 tokens: Apple's MPS backend compiles and caches a graph per
        # tensor shape, and free label lengths (10-443 tokens) grew that cache past the memory cap.
        # Seven shapes instead of hundreds; the padding is masked out of the loss below.
        labels_batch = self.processor.tokenizer(
            [x["text"] for x in items], padding=True, pad_to_multiple_of=64, return_tensors="pt")
        # -100 tells the loss function to ignore padding
        labels = labels_batch.input_ids.masked_fill(labels_batch.attention_mask.ne(1), -100)

        # The model prepends <|startoftranscript|> itself when it shifts
        # labels right, so drop it from the labels if every row has it
        if (labels[:, 0] == self.processor.tokenizer.convert_tokens_to_ids(
                "<|startoftranscript|>")).all():
            labels = labels[:, 1:]
        return {"input_features": feats, "labels": labels}


def build_model(base_model, init_adapter, lora_r, grad_ckpt):
    # Eager attention: on Apple MPS it trains ~19% faster than SDPA
    # (5.64 vs 4.74 clips/s, whisper-base, batch 4) and uses less memory
    model = WhisperForConditionalGeneration.from_pretrained(
        base_model, attn_implementation="eager")
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []
    model.config.use_cache = False          # required with gradient checkpointing

    if grad_ckpt:
        # use_reentrant=False: with the reentrant version and a frozen base,
        # LoRA layers inside checkpointed blocks silently get no gradient
        model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False})

    if init_adapter:
        print("MULTISTAGE: continuing from", init_adapter)
        model = PeftModel.from_pretrained(model, init_adapter, is_trainable=True)
    else:
        print("DIRECT: creating a fresh adapter")
        model = get_peft_model(model, LoraConfig(
            r=lora_r,
            lora_alpha=lora_r * 2,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=0.05,
            bias="none",
        ))
    model.print_trainable_parameters()
    return model


def save_checkpoint(model, opt, sched, step, ckpt_dir):
    model.save_pretrained(ckpt_dir)
    torch.save({"opt": opt.state_dict(), "sched": sched.state_dict(), "step": step},
               os.path.join(ckpt_dir, "trainer_state.pt"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data",         required=True, help="data_prep.py parquet file")
    p.add_argument("--language",     required=True,
                   help="Whisper language NAME: hindi|marathi|kannada|bengali|english")
    p.add_argument("--out",          required=True, help="run directory, e.g. runs/D-odia")
    p.add_argument("--base_model",   default="openai/whisper-base")
    p.add_argument("--init_adapter", default=None,
                   help="Adapter to START from. Set this for MULTISTAGE.")
    p.add_argument("--max_steps",    type=int,   default=2000)
    p.add_argument("--batch_size",   type=int,   default=8)
    p.add_argument("--grad_accum",   type=int,   default=2)
    p.add_argument("--lr",           type=float, default=1e-3)
    p.add_argument("--warmup",       type=int,   default=100)
    p.add_argument("--lora_r",       type=int,   default=32)
    p.add_argument("--precision",    choices=["fp32", "bf16"], default="fp32")
    p.add_argument("--grad_ckpt",    action="store_true")
    p.add_argument("--workers",      type=int,   default=4)
    p.add_argument("--save_every",   type=int,   default=250)
    p.add_argument("--seed",         type=int,   default=42)
    p.add_argument("--max_clips",    type=int,   default=None, help="smoke tests only")
    args = p.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = pick_device()
    os.makedirs(args.out, exist_ok=True)
    ckpt_dir = os.path.join(args.out, "checkpoint")
    if os.path.exists(os.path.join(args.out, "adapter", "adapter_config.json")):
        print("Already trained:", os.path.join(args.out, "adapter"))
        return

    # ---- 1. Processor: sets the <|lang|><|transcribe|><|notimestamps|> prefix ----
    processor = WhisperProcessor.from_pretrained(
        args.base_model, language=args.language, task="transcribe")

    # ---- 2. Data ----
    ds = ParquetSpeech(args.data)
    if args.max_clips:
        ds = torch.utils.data.Subset(ds, range(min(args.max_clips, len(ds))))
    loader = torch.utils.data.DataLoader(
        ds, batch_size=args.batch_size, shuffle=True, drop_last=True,
        num_workers=args.workers, persistent_workers=args.workers > 0,
        collate_fn=Collator(processor),
        generator=torch.Generator().manual_seed(args.seed))

    # ---- 3. Model (resume from our own checkpoint if one exists) ----
    resume = os.path.exists(os.path.join(ckpt_dir, "trainer_state.pt"))
    model = build_model(args.base_model, ckpt_dir if resume else args.init_adapter,
                        args.lora_r, args.grad_ckpt).to(device)
    model.train()

    params = [q for q in model.parameters() if q.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
    sched = get_linear_schedule_with_warmup(opt, args.warmup, args.max_steps)
    step = 0
    if resume:
        state = torch.load(os.path.join(ckpt_dir, "trainer_state.pt"), map_location=device)
        opt.load_state_dict(state["opt"])
        sched.load_state_dict(state["sched"])
        step = state["step"]
        print(f"RESUMING at step {step}")

    autocast = torch.autocast(device_type=device, dtype=torch.bfloat16,
                              enabled=args.precision == "bf16")

    with open(os.path.join(args.out, "train_config.json"), "w") as f:
        json.dump({**vars(args), "device": device, "train_clips": len(ds)}, f, indent=2)
    log = open(os.path.join(args.out, "train_log.jsonl"), "a")

    # ---- 4. Train ----
    print(f"Training on {device}: {len(ds)} clips, steps {step}->{args.max_steps}, "
          f"effective batch {args.batch_size * args.grad_accum}")
    batches = iter(loader)
    t0, running, seen, since = time.time(), 0.0, 0, 0
    while step < args.max_steps:
        for _ in range(args.grad_accum):
            try:
                batch = next(batches)
            except StopIteration:
                batches = iter(loader)
                batch = next(batches)
            batch = {k: v.to(device) for k, v in batch.items()}
            with autocast:
                loss = model(**batch).loss / args.grad_accum
            loss.backward()
            running += loss.item()
            seen += batch["labels"].shape[0]

        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        sched.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        since += 1

        if not math.isfinite(running):
            raise SystemExit(f"Loss is {running} at step {step}. Lower --lr or use fp32.")
        if step % 25 == 0 or step == args.max_steps:
            rate = seen / (time.time() - t0)
            entry = {"step": step, "loss": round(running / since, 4),
                     "lr": sched.get_last_lr()[0], "samples_per_sec": round(rate, 2),
                     "eta_min": round((args.max_steps - step) * args.batch_size
                                      * args.grad_accum / rate / 60, 1)}
            print(json.dumps(entry), flush=True)
            log.write(json.dumps(entry) + "\n")
            log.flush()
            running, since = 0.0, 0
        if step % args.save_every == 0 and step < args.max_steps:
            save_checkpoint(model, opt, sched, step, ckpt_dir)

    # ---- 5. Save the adapter (~20 MB) ----
    model.save_pretrained(os.path.join(args.out, "adapter"))
    print("Adapter saved to", os.path.join(args.out, "adapter"))


if __name__ == "__main__":
    main()
