"""
analysis.py - turn results/ into the tables the report needs. Owner: M4.

    python src/analysis.py            # writes results/tables/*.csv and prints them

Tables:
  main.csv          WER/CER per language x method x test set
  gains.csv         transfer gains with paired-bootstrap 95% CIs
  interaction.csv   Hindi-specific gain compared across targets (the research question)
  normalization.csv raw vs contract vs Whisper-normalizer WER, and ranking flips (RQ3)
  odia_tokens.csv   borrowed-token study (RQ2)
  fertility.csv     Whisper tokens per character / word per language
  pivots.csv        how much each pivot stage changed the model
"""
import glob
import json
import os

import numpy as np
import pandas as pd

from langs import TARGETS

OUT = "results/tables"
B = 1000


def raw(run_id, test_set):
    path = f"results/raw/{run_id}__{test_set}.csv"
    return pd.read_csv(path) if os.path.exists(path) else None


def boot_idx(n, key=""):
    # One fixed seed per comparison, so a CI never depends on what was computed before it
    # (a shared stream moved a borderline interval across zero between two runs).
    seed = 42 + sum(ord(c) * (i + 1) for i, c in enumerate(key))
    return np.random.default_rng(seed).integers(0, n, size=(B, n))


def rate(df, idx, unit):
    err, ref = df[f"{unit}_err"].to_numpy(), df[f"ref_{unit}s"].to_numpy()
    return 100 * err[idx].sum(axis=-1) / ref[idx].sum(axis=-1)


def gain_samples(a, b, test_set, unit, idx=None):
    """Bootstrap samples of WER(a) - WER(b) on the same utterances (paired)."""
    ra, rb = raw(a, test_set), raw(b, test_set)
    if ra is None or rb is None:
        return None
    assert (ra.utt_id == rb.utt_id).all(), f"{a} and {b} scored different clips"
    idx = boot_idx(len(ra), f"{a}|{b}|{test_set}") if idx is None else idx
    return rate(ra, idx, unit) - rate(rb, idx, unit), \
        rate(ra, np.arange(len(ra))[None], unit)[0] - rate(rb, np.arange(len(rb))[None], unit)[0]


def ci(samples):
    return np.percentile(samples, [2.5, 97.5]).round(2)


def main_table(df):
    t = df.pivot_table(index=["language", "test_set"], columns="run_id",
                       values="WER_clean", aggfunc="first")
    return t


def gains_table():
    rows = []
    for lang in TARGETS:
        for test_set in ["fleurs", "kathbath"]:
            for unit in ["word", "char"]:
                for name, a, b in [("hindi_pivot_gain", f"D-{lang}", f"H-{lang}"),
                                   ("english_pivot_gain", f"D-{lang}", f"E-{lang}"),
                                   ("hindi_specific", f"E-{lang}", f"H-{lang}")]:
                    res = gain_samples(a, b, test_set, unit)
                    if res is None:
                        continue
                    samples, point = res
                    lo, hi = ci(samples)
                    rows.append({"language": lang, "test_set": test_set,
                                 "metric": "WER" if unit == "word" else "CER",
                                 "gain": name, "points": round(point, 2),
                                 "ci_low": lo, "ci_high": hi,
                                 "significant": bool(lo > 0 or hi < 0)})
    return pd.DataFrame(rows)


def interaction_table():
    """
    Does the Hindi-specific gain (E - H) differ between targets?
    Each language's test set is resampled independently.
    """
    rows = []
    pairs = [("marathi", "kannada"), ("odia", "kannada"), ("marathi", "odia")]
    for test_set in ["fleurs", "kathbath"]:
        for unit in ["word", "char"]:
            per_lang = {}
            for lang in TARGETS:
                res = gain_samples(f"E-{lang}", f"H-{lang}", test_set, unit)
                if res is None:
                    res = gain_samples(f"D-{lang}", f"H-{lang}", test_set, unit)
                    basis = "D-H"
                else:
                    basis = "E-H"
                if res is not None:
                    per_lang[lang] = (res, basis)
            for x, y in pairs:
                if x in per_lang and y in per_lang:
                    (sx, px), bx = per_lang[x]
                    (sy, py), by = per_lang[y]
                    lo, hi = ci(sx - sy)
                    rows.append({"test_set": test_set,
                                 "metric": "WER" if unit == "word" else "CER",
                                 "comparison": f"{x} - {y}", "basis": bx,
                                 "points": round(px - py, 2), "ci_low": lo, "ci_high": hi,
                                 "significant": bool(lo > 0 or hi < 0)})
    return pd.DataFrame(rows)


def normalization_table(df):
    cols = ["run_id", "language", "test_set", "WER_raw", "WER_clean", "WER_whisper_norm"]
    t = df[cols].copy()
    t["punct_effect"] = (t.WER_raw - t.WER_clean).round(2)
    t["whisper_norm_effect"] = (t.WER_whisper_norm - t.WER_clean).round(2)
    flips = []
    for (lang, ts), g in t.groupby(["language", "test_set"]):
        g = g[g.run_id.str[0].isin(list("ZDHE"))]
        orders = {m: tuple(g.sort_values(m).run_id) for m in
                  ["WER_raw", "WER_clean", "WER_whisper_norm"]}
        flips.append({"language": lang, "test_set": ts,
                      "raw_vs_clean_flip": orders["WER_raw"] != orders["WER_clean"],
                      "whisper_vs_clean_flip": orders["WER_whisper_norm"] != orders["WER_clean"],
                      "order_clean": " < ".join(orders["WER_clean"])})
    return t, pd.DataFrame(flips)


def fertility_table():
    from transformers import WhisperTokenizer
    from normalize import normalize_text
    tok = WhisperTokenizer.from_pretrained("openai/whisper-base")
    rows = []
    for path in sorted(glob.glob("data/test_fleurs_*.parquet")):
        lang = path.split("_")[-1].replace(".parquet", "")
        texts = [normalize_text(t) for t in pd.read_parquet(path, columns=["text"]).text]
        n_tok = sum(len(tok(t, add_special_tokens=False).input_ids) for t in texts)
        rows.append({"language": lang,
                     "tokens_per_char": round(n_tok / sum(len(t.replace(" ", "")) for t in texts), 2),
                     "tokens_per_word": round(n_tok / sum(len(t.split()) for t in texts), 2)})
    return pd.DataFrame(rows)


def pivots_table():
    """Loss drop and size of the learned update, per pivot."""
    import torch
    from safetensors.torch import load_file
    rows = []
    for rid in ["P-hindi", "P-english"]:
        log = f"runs/{rid}/train_log.jsonl"
        ad = f"runs/{rid}/adapter/adapter_model.safetensors"
        if not os.path.exists(log) or not os.path.exists(ad):
            continue
        steps = [json.loads(l) for l in open(log)]
        w = load_file(ad)
        norm = 0.0
        for k in w:
            if "lora_A" in k:
                a, b = w[k].float(), w[k.replace("lora_A", "lora_B")].float()
                norm += torch.linalg.matrix_norm(b @ a * 2.0).item() ** 2   # alpha/r = 2
        rows.append({"pivot": rid, "first_loss": steps[0]["loss"], "last_loss": steps[-1]["loss"],
                     "lora_update_norm": round(norm ** 0.5, 2)})
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_csv("results/results_master.csv")
    tables = {"main": main_table(df).reset_index(), "gains": gains_table(),
              "interaction": interaction_table(), "pivots": pivots_table(),
              "odia_tokens": df[df.language == "odia"][
                  ["run_id", "lang_token", "test_set", "WER_clean", "CER_clean", "script_valid"]]}
    tables["normalization"], tables["ranking_flips"] = normalization_table(df)
    if glob.glob("data/test_fleurs_*.parquet"):
        tables["fertility"] = fertility_table()
    for name, t in tables.items():
        t.to_csv(f"{OUT}/{name}.csv", index=False)
        print(f"\n== {name} ==\n{t.to_string(index=False)}")


if __name__ == "__main__":
    main()
