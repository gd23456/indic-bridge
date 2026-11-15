"""
status.py - one-screen view of the whole pipeline.

    python src/status.py           # print once
    python src/status.py --watch   # refresh every 15 s (Ctrl-C to quit)
"""
import glob
import json
import os
import sys
import time

import pandas as pd

from experiments import load_config, runs


def bar(frac, width=30):
    n = int(frac * width)
    return "█" * n + "░" * (width - n)


def training_line(run_id, max_steps):
    log = f"runs/{run_id}/train_log.jsonl"
    if not os.path.exists(log):
        return "starting…"
    lines = open(log).read().splitlines()
    if not lines:
        return "starting…"
    e = json.loads(lines[-1])
    first = json.loads(lines[0])["loss"]
    return (f"{bar(e['step'] / max_steps)} step {e['step']}/{max_steps}  "
            f"loss {first:.3f}→{e['loss']:.3f}  {e['samples_per_sec']} clips/s  "
            f"ETA {e['eta_min']:.0f} min")


def show():
    cfg = load_config()
    grid = runs()
    print(f"IndicBridge · {time.strftime('%a %H:%M:%S')} · {cfg['base_model']} · "
          f"pivot {cfg['pivot_steps']} / target {cfg['target_steps']} steps\n")

    print("RUNS")
    for r in grid:
        rid = r["id"]
        if os.path.exists(f"runs/{rid}/DONE"):
            state = "✓ done"
        elif os.path.exists(f"runs/{rid}/GATE_FAILED"):
            state = "✗ GATE FAILED"
        elif r["kind"] == "train" and os.path.exists(f"runs/{rid}/train_log.jsonl") \
                and not os.path.exists(f"runs/{rid}/adapter"):
            state = "▶ " + training_line(rid, cfg[r["steps"]])
        elif os.path.exists(f"runs/{rid}/log.txt"):
            state = "▶ evaluating"
        else:
            state = "· waiting"
        print(f"  {rid:18s} {state}")

    print("\nDATA")
    for f in sorted(glob.glob("data/*.json")):
        d = json.load(open(f))
        print(f"  {d['name']:24s} {d['clips']:6d} clips  {d['hours']:6.2f} h")
    if glob.glob("data/_shards/**/*.parquet", recursive=True):
        print("  … downloading a shard")

    path = "results/results_master.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        print("\nRESULTS (WER / CER after normalization, %)")
        t = df.pivot_table(index="run_id", columns="test_set",
                           values=["WER_clean", "CER_clean"], aggfunc="first")
        t.columns = [f"{m.split('_')[0]}·{s}" for m, s in t.columns]
        order = [r["id"] for r in grid if r["id"] in t.index]
        print(t.loc[order].round(1).to_string())


if __name__ == "__main__":
    if "--watch" in sys.argv:
        while True:
            os.system("clear")
            show()
            time.sleep(15)
    else:
        show()
