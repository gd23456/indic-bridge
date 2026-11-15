"""
store.py - everything the demo reads: test clips, scored outputs, results,
tokenizer facts. Read-only over data/, results/ and mlx_models/.

Every number the demo shows comes from here, so it comes from those files.
"""
import functools
import io
import threading
import json
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import jiwer  # noqa: E402

from audio import decode  # noqa: E402
from langs import LANGS, ODIA_MAIN_TOKEN, ODIA_TOKENS, TARGETS  # noqa: E402
from normalize import normalize_text  # noqa: E402

LANGUAGES = ["hindi"] + TARGETS
TEST_SETS = ["fleurs", "kathbath"]
METHODS = [  # lane order: what each target language is compared across
    ("Z", "zeroshot", "Zero-shot", "none"),
    ("D", "direct_lora", "Direct", "none"),
    ("H", "multistage_lora", "Hindi → target", "hindi"),
    ("E", "multistage_lora", "English → target", "english"),
]


def path(*p):
    return os.path.join(ROOT, *p)


def _mtime(p):
    return os.path.getmtime(p) if os.path.exists(p) else 0.0


# ------------------------------------------------------------------ #
#  Clips                                                              #
# ------------------------------------------------------------------ #

@functools.lru_cache(maxsize=16)
def _table(test_set, language):
    p = path("data", f"test_{test_set}_{language}.parquet")
    if not os.path.exists(p):
        return None
    t = pq.read_table(p, columns=["utt_id", "duration", "text"]).to_pandas()
    t["index"] = range(len(t))
    return t


def clips(test_set, language):
    t = _table(test_set, language)
    if t is None:
        return []
    return [{"utt_id": r.utt_id, "index": int(r.index), "duration": round(float(r.duration), 2),
             "text": r.text} for r in t.itertuples()]


class UnknownClip(KeyError):
    pass


def clip_index(test_set, language, utt_id):
    t = _table(test_set, language)
    hits = t.index[t.utt_id == utt_id] if t is not None else []
    if len(hits) == 0:
        raise UnknownClip(f"Clip {utt_id} is not in the {language.title()} {test_set} test set")
    return int(hits[0])


def clip_audio(test_set, language, utt_id):
    """float32 16 kHz array for one test clip."""
    t = _table(test_set, language)
    idx = clip_index(test_set, language, utt_id)
    col = pq.read_table(path("data", f"test_{test_set}_{language}.parquet"),
                        columns=["audio"]).column("audio")
    return decode(col[idx].as_py()), t.text.iloc[idx]


def wav_bytes(array):
    buf = io.BytesIO()
    sf.write(buf, array, 16000, format="WAV", subtype="PCM_16")
    return buf.getvalue()


# ------------------------------------------------------------------ #
#  Alignment: where a hypothesis is wrong, word by word               #
# ------------------------------------------------------------------ #

def align(reference, hypothesis):
    """Word ops on contract-normalized text, plus WER/CER for this one clip."""
    r, h = normalize_text(reference), normalize_text(hypothesis or "")
    if not r:
        return {"ops": [], "wer": None, "cer": None}
    words = jiwer.process_words(r, h)
    rw, hw = r.split(), h.split()
    ops = []
    for c in words.alignments[0]:
        ops.append({"type": c.type,
                    "ref": rw[c.ref_start_idx:c.ref_end_idx],
                    "hyp": hw[c.hyp_start_idx:c.hyp_end_idx]})
    chars = jiwer.process_characters(r, h)
    return {"ops": ops,
            "wer": round(100 * (words.substitutions + words.deletions + words.insertions) / len(rw), 1),
            "cer": round(100 * (chars.substitutions + chars.deletions + chars.insertions) / len(r), 1)}


# ------------------------------------------------------------------ #
#  Scored outputs (results/raw), as the results table saw them        #
# ------------------------------------------------------------------ #

def run_id(prefix, language):
    if prefix == "Z":
        return f"Z-{language}-{ODIA_MAIN_TOKEN}" if language == "odia" else f"Z-{language}"
    if language == "hindi":
        return {"D": "P-hindi"}.get(prefix)      # Hindi's only trained model is the pivot
    return f"{prefix}-{language}"


@functools.lru_cache(maxsize=64)
def _raw(rid, test_set, stamp):
    p = path("results", "raw", f"{rid}__{test_set}.csv")
    return pd.read_csv(p, keep_default_na=False).set_index("utt_id") if os.path.exists(p) else None


def raw(rid, test_set):
    p = path("results", "raw", f"{rid}__{test_set}.csv")
    return _raw(rid, test_set, _mtime(p))


def lanes(test_set, language, utt_id):
    """The same clip through every method, from the scored runs."""
    t = _table(test_set, language)
    reference = t.text.iloc[clip_index(test_set, language, utt_id)]
    out = []
    for prefix, method, label, pivot in METHODS:
        rid = run_id(prefix, language)
        if rid is None:
            continue
        if language == "hindi" and prefix == "D":
            label = "Fine-tuned (the 45 h Hindi pivot)"
        elif pivot != "none":
            label = f"{pivot.title()} → {language.title()}"
        df = raw(rid, test_set)
        if df is None or utt_id not in df.index:
            out.append({"run_id": rid, "method": method, "label": label, "pivot": pivot,
                        "status": "not_run"})
            continue
        hyp = df.loc[utt_id, "hypothesis"]
        out.append({"run_id": rid, "method": method, "label": label, "pivot": pivot,
                    "status": "scored", "hypothesis": hyp,
                    "script_valid": script_share(hyp, language), **align(reference, hyp)})
    return {"reference": reference, "lanes": out}


def script_share(text, language):
    lo, hi = LANGS[language]["script"]
    letters = [c for c in text if c.isalpha() or 0x0900 <= ord(c) <= 0x0DFF]
    return round(100 * sum(lo <= ord(c) <= hi for c in letters) / len(letters), 1) if letters else 0.0


def showcase(language, test_set="fleurs"):
    """
    The first viewport's clip: a TYPICAL one, never the most flattering. Among
    clips that fit a viewport (4-9 s, 5-12 words), pick the one where every
    scored method's error is closest to that method's own average.
    """
    t = _table(test_set, language)
    if t is None:
        return None
    words = t.text.str.split().str.len()
    cand = t[t.duration.between(4, 9) & words.between(5, 12)]
    cand = cand if len(cand) else t
    errs = []
    for prefix, *_ in METHODS:
        rid = run_id(prefix, language)
        df = raw(rid, test_set) if rid else None
        if df is not None:
            e = df.word_err / df.ref_words.clip(lower=1)
            errs.append((e - e.mean()).abs())
    if not errs:
        return cand.utt_id.iloc[len(cand) // 2]
    distance = sum(e.reindex(cand.utt_id).fillna(10) for e in errs)
    return distance.idxmin()


# ------------------------------------------------------------------ #
#  Results                                                            #
# ------------------------------------------------------------------ #

def results():
    p = path("results", "results_master.csv")
    if not os.path.exists(p):
        return []
    df = pd.read_csv(p).replace({np.nan: None})
    return df.to_dict(orient="records")


@functools.lru_cache(maxsize=64)
def _gain(a, b, test_set, unit, stamp):
    from analysis import ci, gain_samples
    res = gain_samples(a, b, test_set, unit)
    if res is None:
        return None
    samples, point = res
    lo, hi = ci(samples)
    return {"points": round(float(point), 2), "ci_low": float(lo), "ci_high": float(hi)}


def gains():
    """Transfer gains (positive = the second run has fewer errors), 95% paired bootstrap CI."""
    rows = []
    for language in TARGETS:
        for test_set in TEST_SETS:
            for unit, metric in [("word", "WER"), ("char", "CER")]:
                for name, a, b in [("hindi_pivot", f"D-{language}", f"H-{language}"),
                                   ("english_pivot", f"D-{language}", f"E-{language}"),
                                   ("hindi_specific", f"E-{language}", f"H-{language}")]:
                    stamp = (_mtime(path("results", "raw", f"{a}__{test_set}.csv")),
                             _mtime(path("results", "raw", f"{b}__{test_set}.csv")))
                    g = _gain(a, b, test_set, unit, stamp)
                    rows.append({"language": language, "test_set": test_set, "metric": metric,
                                 "gain": name, **(g or {"points": None})})
    return rows


_tok = None
_tok_lock = threading.Lock()


def _tokenizer():
    # Transformers' lazy imports are not thread-safe: two requests importing it at once
    # (the page asks for Odia and Hindi tokens together) made one fail. Load once, locked.
    global _tok
    with _tok_lock:
        if _tok is None:
            from transformers import WhisperTokenizer
            _tok = WhisperTokenizer.from_pretrained("openai/whisper-base")
    return _tok


def tokens(text):
    """Whisper's tokens for a sentence, each as the UTF-8 bytes it holds."""
    tok = _tokenizer()
    out = []
    for piece in tok.convert_ids_to_tokens(tok(text, add_special_tokens=False).input_ids):
        raw_bytes = bytes(tok.byte_decoder[c] for c in piece)
        try:
            shown = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            shown = None                      # part of a letter: only bytes
        out.append({"hex": raw_bytes.hex(" "), "text": shown})
    letters = len(text.replace(" ", ""))
    return {"text": text, "tokens": out, "letters": letters,
            "per_letter": round(len(out) / max(letters, 1), 2)}


def facts():
    """Measured facts for the story: fertility and decoder-limit exclusions."""
    stamp = tuple(_mtime(path("data", f"test_fleurs_{l}.json")) for l in LANGUAGES)
    return _facts(stamp)


@functools.lru_cache(maxsize=2)
def _facts(stamp):
    out = {}
    for language in LANGUAGES:
        t = _table("fleurs", language)
        meta = path("data", f"test_fleurs_{language}.json")
        d = json.load(open(meta)) if os.path.exists(meta) else {}
        row = {"too_long_pct": d.get("split_too_long_pct"),
               "too_long": d.get("split_too_long_for_decoder"),
               "split_clips": d.get("split_clips")}
        if t is not None:
            tok = _tokenizer()
            texts = [normalize_text(x) for x in t.text]
            n = sum(len(tok(x, add_special_tokens=False).input_ids) for x in texts)
            row["tokens_per_letter"] = round(n / sum(len(x.replace(" ", "")) for x in texts), 2)
            row["tokens_per_word"] = round(n / sum(len(x.split()) for x in texts), 2)
        out[language] = row
    return out


def odia_tokens():
    rows = [r for r in results() if r["run_id"] in {f"Z-odia-{t}" for t in ODIA_TOKENS}
            or str(r["run_id"]).startswith("T-odia") or r["run_id"] == "D-odia"]
    return rows


def models():
    p = path("mlx_models", "manifest.json")
    return json.load(open(p)) if os.path.exists(p) else {}
