"""
data_prep.py - build every training and test set as local parquet files.

CONTRACT FILE. Owner: M3.

Output: data/<name>.parquet, one row per clip, columns
    utt_id, speaker_id, duration, text, audio   (audio = 16 kHz mono FLAC bytes)

Usage:
    python src/data_prep.py train --language hindi   --hours 45   # IndicVoices
    python src/data_prep.py train --language english --hours 45   # LibriSpeech clean-100
    python src/data_prep.py test  --language odia                 # FLEURS test + Kathbath valid
    python src/data_prep.py inspect --language odia               # print 10 raw rows, download nothing big

Why not load_dataset("ai4bharat/IndicVoices", lang)? Each language is
36-59 GB and that call downloads all of it. Instead we read a seeded
sample of parquet shards spread over the whole shard range, filter on
metadata (duration, text, label length, speaker) without decoding audio,
then decode only the clips we keep. Shards are deleted after use.
"""
import argparse
import json
import os
import random
import re
import shutil
import sys
import unicodedata
from multiprocessing import Pool

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi, hf_hub_download
from transformers import WhisperTokenizer

from audio import to_flac_16k

DATA_DIR = "data"
TMP_DIR = os.path.join(DATA_DIR, "_shards")

MIN_SECONDS = 1.0     # shorter clips cause hallucination
# Training only: IndicVoices has many 1-2 s backchannels ("haan haan").
# Whisper pays for a full 30 s window per clip, so these cost as much as a
# sentence and teach little. Same threshold for every language.
MIN_TRAIN_SECONDS = 2.0
MAX_SECONDS = 30.0    # Whisper's context window
MAX_LABEL_TOKENS = 448 - 5   # decoder limit minus 4 prompt tokens and <|endoftext|>
SEED = 42

SOURCES = {
    # repo, shard prefix template, column names (audio, text, duration, speaker)
    "indicvoices": ("ai4bharat/IndicVoices", "{lang}/train-",
                    ("audio_filepath", "text", "duration", "speaker_id")),
    "librispeech": ("openslr/librispeech_asr", "clean/train.100/",
                    ("audio", "text", None, "speaker_id")),
    "kathbath":    ("ai4bharat/Kathbath", "{lang}/valid-",
                    ("audio_filepath", "text", "duration", "speaker_id")),
    "fleurs":      ("google/fleurs", "parquet-data/{lang}/test-",
                    ("audio", "raw_transcription", "num_samples", None)),
}

TAG_RE = re.compile(r"\[[^\]]*\]|<[^>]*>|\{[^}]*\}")
WHITESPACE_RE = re.compile(r"\s+")

_tokenizer = None


def clean_train_text(text):
    """Training targets: NFC, no annotation tags, single spaces. Punctuation is kept."""
    text = unicodedata.normalize("NFC", text or "")
    text = TAG_RE.sub(" ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def label_tokens(texts):
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = WhisperTokenizer.from_pretrained("openai/whisper-base")
    return [len(ids) for ids in _tokenizer(texts, add_special_tokens=False).input_ids]


def list_shards(source, lang):
    repo, prefix, _ = SOURCES[source]
    prefix = prefix.format(lang=lang)
    files = HfApi().list_repo_files(repo, repo_type="dataset")
    shards = sorted(f for f in files if f.startswith(prefix) and f.endswith(".parquet"))
    if not shards:
        sys.exit(f"No shards for {source}/{lang} under '{prefix}'. "
                 "Gated? Accept the terms on the dataset page and run `hf auth login`.")
    return repo, shards


def fetch(repo, path):
    return hf_hub_download(repo, path, repo_type="dataset", local_dir=TMP_DIR)


def read_metadata(local, source):
    """Every column except the audio bytes - cheap, because parquet is columnar."""
    audio_col, text_col, dur_col, spk_col = SOURCES[source][2]
    cols = [c for c in (text_col, dur_col, spk_col) if c]
    meta = pq.read_table(local, columns=cols).to_pydict()
    n = len(meta[text_col])
    if dur_col == "num_samples":                          # FLEURS
        durations = [s / 16000 for s in meta[dur_col]]
    elif dur_col:
        durations = meta[dur_col]
    else:                                                 # LibriSpeech: measured after decode
        durations = [None] * n
    speakers = meta[spk_col] if spk_col else [None] * n
    tagged = [bool(TAG_RE.search(t or "")) for t in meta[text_col]]
    texts = [clean_train_text(t) for t in meta[text_col]]
    return texts, durations, [str(s) for s in speakers], tagged


def encode_rows(local, source, rows):
    audio_col = SOURCES[source][2][0]
    audio = pq.read_table(local, columns=[audio_col]).column(audio_col).take(rows).to_pylist()
    # PREP_WORKERS=3 while a training run needs the CPU for its data loaders
    workers = int(os.environ.get("PREP_WORKERS", max(1, (os.cpu_count() or 4) - 2)))
    with Pool(workers) as pool:
        return pool.map(to_flac_16k, [a["bytes"] for a in audio], chunksize=16)


def write(rows, name, stats):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{name}.parquet")
    table = pa.table({k: [r[k] for r in rows] for k in
                      ("utt_id", "speaker_id", "duration", "text", "audio")})
    pq.write_table(table, path)
    stats.update(name=name, clips=len(rows),
                 hours=round(sum(r["duration"] for r in rows) / 3600, 3),
                 speakers=len({r["speaker_id"] for r in rows}))
    with open(os.path.join(DATA_DIR, f"{name}.json"), "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return path


# ------------------------------------------------------------------ #
#  Training sets                                                      #
# ------------------------------------------------------------------ #

def build_train(language, hours, n_shards, max_per_speaker, lowercase=False):
    """
    Take hours/n_shards from each of n_shards seeded shards, filtered and
    speaker-capped, so the sample spans speakers and districts instead of
    being the first N clips of one shard. Keeps fetching shards until the
    budget is met.
    """
    source = "librispeech" if language == "english" else "indicvoices"
    repo, shards = list_shards(source, language)
    rng = random.Random(SEED)
    rng.shuffle(shards)

    budget = hours * 3600
    per_shard = budget / n_shards
    per_speaker = {}
    kept, total = [], 0.0
    dropped = {"duration": 0, "empty_text": 0, "tagged": 0, "label_too_long": 0,
               "speaker_cap": 0, "undecodable": 0}

    for shard in shards:
        if total >= budget:
            break
        local = fetch(repo, shard)
        texts, durations, speakers, tagged = read_metadata(local, source)
        if lowercase:
            texts = [t.lower() for t in texts]
        n_tok = label_tokens(texts)

        candidates = []
        for i, (t, d, s, k) in enumerate(zip(texts, durations, speakers, n_tok)):
            if not t:
                dropped["empty_text"] += 1
            elif tagged[i]:
                # <unintelligible>: the audio holds speech the text does not
                dropped["tagged"] += 1
            elif d is not None and not (MIN_TRAIN_SECONDS <= d <= MAX_SECONDS):
                dropped["duration"] += 1
            elif k > MAX_LABEL_TOKENS:
                dropped["label_too_long"] += 1
            else:
                candidates.append(i)
        rng.shuffle(candidates)

        take, shard_secs = [], 0.0
        for i in candidates:
            if shard_secs >= min(per_shard, budget - total):
                break
            if per_speaker.get(speakers[i], 0) >= max_per_speaker:
                dropped["speaker_cap"] += 1
                continue
            per_speaker[speakers[i]] = per_speaker.get(speakers[i], 0) + 1
            take.append(i)
            shard_secs += durations[i] if durations[i] is not None else 12.0

        for i, (flac, secs) in zip(take, encode_rows(local, source, take)):
            if flac is None or not (MIN_TRAIN_SECONDS <= secs <= MAX_SECONDS):
                dropped["undecodable" if flac is None else "duration"] += 1
                continue
            kept.append({"utt_id": f"{language}-{os.path.basename(shard)}-{i}",
                         "speaker_id": speakers[i], "duration": secs,
                         "text": texts[i], "audio": flac})
            total += secs
        print(f"{shard}: kept {len(take)} clips, total {total/3600:.2f} h")
        os.remove(local)

    shutil.rmtree(TMP_DIR, ignore_errors=True)
    if total < budget * 0.98:
        print(f"WARNING: only {total/3600:.2f} h available, budget was {hours} h")
    name = f"train_{language}_{int(hours)}h"
    return write(kept, name, {"source": repo, "language": language,
                              "budget_hours": hours, "dropped": dropped,
                              "min_train_seconds": MIN_TRAIN_SECONDS,
                              "max_per_speaker": max_per_speaker})


# ------------------------------------------------------------------ #
#  Test sets                                                          #
# ------------------------------------------------------------------ #

def build_test(source, language, max_utts):
    """
    A fixed, seeded sample of at most max_utts clips. Never used for training.
    FLEURS: reference is raw_transcription (with punctuation) so the
    raw-vs-clean WER gap measures the punctuation effect on both sides.
    """
    from langs import LANGS
    lang = LANGS[language]["fleurs"] if source == "fleurs" else language
    repo, shards = list_shards(source, lang)
    rows, n_total, n_too_long = [], 0, 0
    for shard in shards:
        local = fetch(repo, shard)
        texts, durations, speakers, _ = read_metadata(local, source)
        n_tok = label_tokens(texts)
        ok = [i for i, (t, d) in enumerate(zip(texts, durations))
              if t and MIN_SECONDS <= d <= MAX_SECONDS]
        n_total += len(ok)
        # A reference longer than the decoder can hold is unreachable for
        # every model, so it is excluded for every language and method.
        n_too_long += sum(n_tok[i] > MAX_LABEL_TOKENS for i in ok)
        ok = [i for i in ok if n_tok[i] <= MAX_LABEL_TOKENS]
        rows += [(local, i, texts[i], speakers[i]) for i in ok]
    rng = random.Random(SEED)
    rng.shuffle(rows)
    rows = sorted(rows[:max_utts], key=lambda r: (r[0], r[1]))

    kept = []
    for local in sorted({r[0] for r in rows}):
        mine = [r for r in rows if r[0] == local]
        encoded = encode_rows(local, source, [r[1] for r in mine])
        for (_, i, text, spk), (flac, secs) in zip(mine, encoded):
            if flac is not None:
                kept.append({"utt_id": f"{source}-{language}-{os.path.basename(local)}-{i}",
                             "speaker_id": spk, "duration": secs, "text": text, "audio": flac})
        os.remove(local)
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    return write(kept, f"test_{source}_{language}", {
        "source": repo, "language": language, "max_utts": max_utts,
        "split_clips": n_total, "split_too_long_for_decoder": n_too_long,
        "split_too_long_pct": round(100 * n_too_long / max(n_total, 1), 2)})


def inspect(language, n=10):
    """Show raw rows from one shard so we can check the text columns by eye."""
    source = "librispeech" if language == "english" else "indicvoices"
    repo, shards = list_shards(source, language)
    local = fetch(repo, shards[0])
    cols = [c for c in pq.read_schema(local).names if c != SOURCES[source][2][0]]
    table = pq.read_table(local, columns=cols).slice(0, n).to_pylist()
    for row in table:
        print(json.dumps(row, ensure_ascii=False)[:600])
    os.remove(local)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["train", "test", "inspect"])
    p.add_argument("--language", required=True)  # hindi|marathi|kannada|odia|english
    p.add_argument("--hours", type=float, default=15.0)
    p.add_argument("--n_shards", type=int, default=None,
                   help="Shards to spread the sample over (default: 1 per 7.5 h)")
    p.add_argument("--max_per_speaker", type=int, default=50)
    p.add_argument("--max_utts", type=int, default=600)
    p.add_argument("--sets", nargs="+", default=["fleurs", "kathbath"])
    a = p.parse_args()

    if a.mode == "inspect":
        inspect(a.language)
    elif a.mode == "train":
        build_train(a.language, a.hours, a.n_shards or max(2, round(a.hours / 7.5)),
                    a.max_per_speaker, lowercase=(a.language == "english"))
    else:
        for source in a.sets:
            build_test(source, a.language, a.max_utts)
