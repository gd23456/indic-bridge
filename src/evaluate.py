"""
evaluate.py - the ONLY scoring script for this project.
Every experiment must call score_run() from here.

CONTRACT FILE. Owner: M2.
"""
import os
import datetime

import jiwer
import pandas as pd
from transformers.models.whisper.english_normalizer import BasicTextNormalizer

from normalize import normalize_text, CONTRACT_VERSION
from langs import LANGS

RESULTS_PATH = "results/results_master.csv"

RESULT_COLUMNS = [
    "run_id", "language", "method", "pivot", "lang_token", "base_model",
    "train_hours", "train_steps", "test_set",
    "WER_raw", "WER_clean", "CER_raw", "CER_clean", "WER_whisper_norm",
    "punct_gain", "script_valid", "n_samples", "date", "norm_version",
]

# Whisper's own normalizer replaces every Unicode "Mark" character with a
# space. In Indic scripts the vowel signs, virama and anusvara are Marks,
# so it shatters words into fragments. We never score with it, but we
# report what it does to the numbers (RQ3).
_whisper_norm = BasicTextNormalizer()


def _wer_cer(refs, hyps):
    # Drop pairs with an empty reference - WER is undefined for them
    pairs = [(r, h) for r, h in zip(refs, hyps) if r.strip()]
    if not pairs:
        return float("nan"), float("nan"), 0
    refs, hyps = zip(*pairs)
    return (round(jiwer.wer(list(refs), list(hyps)) * 100, 2),
            round(jiwer.cer(list(refs), list(hyps)) * 100, 2),
            len(refs))


def score_all(references, hypotheses, remove_punct=True):
    """
    references : list of correct sentences
    hypotheses : list of model outputs
    returns    : dict with WER and CER as percentages
    """
    assert len(references) == len(hypotheses), "lists must be the same length"
    refs = [normalize_text(r, remove_punct) for r in references]
    hyps = [normalize_text(h, remove_punct) for h in hypotheses]
    wer, cer, n = _wer_cer(refs, hyps)
    return {"WER": wer, "CER": cer, "n_samples": n}


def script_validity(hypotheses, language):
    """
    Share of letters in the outputs that belong to the target script.
    Makes "Odia audio came out in Bengali script" a number, not a screenshot.
    """
    block = LANGS[language]["script"]
    if block is None:
        return float("nan")
    lo, hi = block
    letters = [c for h in hypotheses for c in h if c.isalpha() or 0x0900 <= ord(c) <= 0x0DFF]
    if not letters:
        return 0.0
    inside = sum(lo <= ord(c) <= hi for c in letters)
    return round(100 * inside / len(letters), 2)


def score_run(references, hypotheses, language):
    """
    Report every number, like the reference paper did and more.
    raw vs clean = punctuation effect; clean vs whisper_norm = what the
    default Whisper normalizer would have told us instead.
    """
    raw = score_all(references, hypotheses, remove_punct=False)
    clean = score_all(references, hypotheses, remove_punct=True)
    wn, _, _ = _wer_cer([_whisper_norm(r) for r in references],
                        [_whisper_norm(h) for h in hypotheses])
    return {
        "WER_raw": raw["WER"],
        "WER_clean": clean["WER"],
        "CER_raw": raw["CER"],
        "CER_clean": clean["CER"],
        "WER_whisper_norm": wn,
        "punct_gain": round(raw["WER"] - clean["WER"], 2),
        "script_valid": script_validity(hypotheses, language),
        "n_samples": clean["n_samples"],
        "norm_version": CONTRACT_VERSION,
    }


def per_utterance_errors(references, hypotheses):
    """
    Word and character edit counts per utterance, on normalized text.
    analysis.py resamples these for paired bootstrap confidence intervals.
    """
    rows = []
    for r, h in zip(references, hypotheses):
        rn, hn = normalize_text(r), normalize_text(h)
        if not rn:
            rows.append((rn, hn, 0, 0, 0, 0))
            continue
        w = jiwer.process_words(rn, hn)
        c = jiwer.process_characters(rn, hn)
        rows.append((rn, hn,
                     w.substitutions + w.deletions + w.insertions, len(rn.split()),
                     c.substitutions + c.deletions + c.insertions, len(rn)))
    return pd.DataFrame(rows, columns=["ref_norm", "hyp_norm", "word_err",
                                       "ref_words", "char_err", "ref_chars"])


def save_result(row, path=RESULTS_PATH):
    """Write one result row; re-running the same run and test set replaces it."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    row = {**row, "date": datetime.date.today().isoformat()}
    for col in RESULT_COLUMNS:
        row.setdefault(col, "")
    df_new = pd.DataFrame([row])[RESULT_COLUMNS]
    if os.path.exists(path):
        df = pd.read_csv(path)
        df = df[~((df.run_id == row["run_id"]) & (df.test_set == row["test_set"]))]
        df = pd.concat([df, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_csv(path, index=False)
    print(f"Saved. Table now has {len(df)} rows.")
    return df


def save_raw(utt_ids, references, hypotheses, tag, folder="results/raw"):
    """Save per-sample outputs. Error analysis and bootstrap need these."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{tag}.csv")
    df = pd.DataFrame({"utt_id": utt_ids, "reference": references,
                       "hypothesis": hypotheses})
    df = pd.concat([df, per_utterance_errors(references, hypotheses)], axis=1)
    df.to_csv(path, index=False)
    print("Raw outputs saved to", path)
    return path
