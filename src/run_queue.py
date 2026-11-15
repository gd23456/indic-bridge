"""
run_queue.py - run the whole grid on this machine, one job at a time.

    caffeinate -dimsu python src/run_queue.py            # everything that is ready
    python src/run_queue.py --dry                        # print the plan, run nothing
    python src/run_queue.py --only P-hindi X-hindi-odia  # selected runs

Resumable: a finished run leaves runs/<id>/DONE and is skipped next time;
an interrupted training run resumes from its last checkpoint. Runs whose
inputs are not ready yet (data not prepared, pivot not trained) are
skipped, so the queue can simply be started again later.
"""
import argparse
import json
import os
import subprocess
import sys

import pandas as pd

from experiments import TEST_SETS, load_config, odia_token, runs
from langs import ODIA_TOKENS

PY = sys.executable
# Cap MPS memory so an oversized batch fails fast instead of swapping the Mac
ENV = {**os.environ, "PYTORCH_ENABLE_MPS_FALLBACK": "1", "PYTORCH_MPS_HIGH_WATERMARK_RATIO": "0.8",
       "PYTORCH_MPS_LOW_WATERMARK_RATIO": "0.6"}


def done(run_id):
    return os.path.exists(f"runs/{run_id}/DONE")


def sh(cmd, log_path, dry):
    print("  $", " ".join(cmd))
    if dry:
        return
    with open(log_path, "a") as log:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env=ENV, text=True)
        for line in proc.stdout:
            print("   ", line, end="", flush=True)
            log.write(line)
        if proc.wait() != 0:
            raise RuntimeError(f"failed: {' '.join(cmd)} (see {log_path})")


def results():
    path = "results/results_master.csv"
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["run_id"])


def scored(run_id, test_set):
    df = results()
    return (os.path.exists(f"results/raw/{run_id}__{test_set}.csv")
            and ((df.run_id == run_id) & (df.get("test_set") == test_set)).any())


def record_odia_ranking():
    """Zero-shot ranking of the borrowed tokens, for the report (RQ2)."""
    df = results()
    z = df[df.run_id.isin([f"Z-odia-{t}" for t in ODIA_TOKENS])]
    if len(z) < len(ODIA_TOKENS) * len(TEST_SETS):
        return
    ranking = z.groupby("lang_token").CER_clean.mean().sort_values().round(2)
    with open("results/odia_token_zeroshot_ranking.json", "w") as f:
        json.dump(ranking.to_dict(), f, indent=2)


def resolve_token(run):
    tok = run["token"]
    if tok == "auto":
        return odia_token() if run["language"] == "odia" else run["language"]
    return tok


def check_gate(run):
    """The pivot must beat zero-shot on every test set before anything builds on it."""
    df = results()
    pivot = df[df.run_id == run["id"]].set_index("test_set").WER_clean
    base = df[df.run_id == run["gate"]].set_index("test_set").WER_clean
    ok = all(pivot[t] < base[t] for t in TEST_SETS)
    print(f"GATE {run['id']}: {pivot.to_dict()} vs zero-shot {base.to_dict()} ->",
          "PASS" if ok else "FAIL")
    return ok


def blocked(run, cfg):
    """Reason this run cannot start yet, or None."""
    if run.get("init") and not done(run["init"]):
        return f"waiting for {run['init']}"
    if run.get("adapter") and not done(run["adapter"]):
        return f"waiting for {run['adapter']}"
    if run["kind"] == "train" and not os.path.exists(f"data/{run['data']}.parquet"):
        return f"data/{run['data']}.parquet not prepared"
    if not run.get("no_eval"):
        for t in TEST_SETS:
            if not os.path.exists(f"data/test_{t}_{run['language']}.parquet"):
                return f"data/test_{t}_{run['language']}.parquet not prepared"
    return None


def execute(run, cfg, dry):
    rid, lang, tok = run["id"], run["language"], resolve_token(run)
    os.makedirs(f"runs/{rid}", exist_ok=True)
    log = f"runs/{rid}/log.txt"
    hours, steps, adapter = 0.0, 0, None

    if run["kind"] == "train":
        steps = cfg[run["steps"]]
        cmd = [PY, "src/train_lora.py", "--data", f"data/{run['data']}.parquet",
               "--language", tok, "--out", f"runs/{rid}", "--max_steps", str(steps),
               "--batch_size", str(cfg["batch_size"]), "--grad_accum", str(cfg["grad_accum"]),
               "--precision", cfg["precision"], "--base_model", cfg["base_model"]]
        if cfg["grad_ckpt"]:
            cmd.append("--grad_ckpt")
        if run.get("init"):
            cmd += ["--init_adapter", f"runs/{run['init']}/adapter"]
        sh(cmd, log, dry)
        adapter = f"runs/{rid}/adapter"
        meta = f"data/{run['data']}.json"
        hours = json.load(open(meta))["hours"] if os.path.exists(meta) else 0.0
    elif run.get("adapter"):
        adapter = f"runs/{run['adapter']}/adapter"

    if not run.get("no_eval"):
        for t in TEST_SETS:
            if scored(rid, t):
                print(f"  {rid} on {t}: already scored")
                continue
            cmd = [PY, "src/eval_model.py", "--run_id", rid, "--base_model", cfg["base_model"],
                   "--test", f"data/test_{t}_{lang}.parquet", "--language", tok,
                   "--target_lang", lang, "--method", run["method"], "--pivot", run["pivot"],
                   "--train_hours", str(hours), "--train_steps", str(steps),
                   "--batch_size", str(cfg["eval_batch"]), "--dtype", cfg["eval_dtype"]]
            if adapter:
                cmd += ["--adapter", adapter]
            sh(cmd, log, dry)

    if dry:
        return True
    if run.get("gate") and not check_gate(run):
        open(f"runs/{rid}/GATE_FAILED", "w").close()
        return False
    open(f"runs/{rid}/DONE", "w").close()
    record_odia_ranking()
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--only", nargs="*", help="run ids to run (default: all)")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--retry", action="store_true", help="rerun runs marked FAILED")
    a = p.parse_args()
    cfg = load_config()

    for run in runs():
        if a.only and run["id"] not in a.only:
            continue
        if done(run["id"]):
            continue
        if os.path.exists(f"runs/{run['id']}/FAILED") and not a.retry:
            print(f"[skip] {run['id']}: failed earlier (see runs/{run['id']}/FAILED; --retry to rerun)")
            continue
        reason = blocked(run, cfg)
        if reason:
            print(f"[skip] {run['id']}: {reason}")
            continue
        print(f"\n=== {run['id']} ({run['kind']}, {run['language']}, "
              f"token={resolve_token(run)}) ===", flush=True)
        try:
            ok = execute(run, cfg, a.dry)
        except RuntimeError as e:
            # One failed run must not stop the night: record it and carry on with
            # everything that does not depend on it (dependents stay blocked).
            print(f"FAILED {run['id']}: {e}", flush=True)
            open(f"runs/{run['id']}/FAILED", "w").write(str(e))
            continue
        if not ok:
            sys.exit(f"STOP: {run['id']} failed its gate. Fix the pivot before "
                     "running anything that builds on it.")


if __name__ == "__main__":
    main()
