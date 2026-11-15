"""
error_sample.py - pick 50 wrong outputs per language for native-speaker
error analysis, with the audio saved next to them for listening.

    python src/error_sample.py --language odia            # FLEURS, D vs H runs

Writes results/error_analysis/<language>_50.csv and <language>_audio/<n>.wav.
Each row shows the direct and the multistage output for the same clip, so
the annotator can say which error types multistage fixed. For Hindi the pair
is zero-shot vs the fine-tuned pivot. Columns keep the names direct /
multistage; the runs column says which runs they are.

Categories (one or more per row, separated by '|'):
  SCRIPT  PHONETIC  MORPHOLOGY  SEGMENTATION  CODE_SWITCH  NUMBER
  HALLUCINATION  REFERENCE_WRONG
"""
import argparse
import os

import pandas as pd
import pyarrow.parquet as pq
import soundfile as sf

from audio import decode

p = argparse.ArgumentParser()
p.add_argument("--language", required=True)
p.add_argument("--test_set", default="fleurs")
p.add_argument("--n", type=int, default=50)
p.add_argument("--before", default=None, help="run id in the first column (default D-<language>)")
p.add_argument("--after", default=None, help="run id in the second column (default H-<language>)")
a = p.parse_args()
# Hindi has no direct/multistage pair: compare zero-shot with the fine-tuned pivot instead
default = ("Z-hindi", "P-hindi") if a.language == "hindi" else (f"D-{a.language}", f"H-{a.language}")
before, after = a.before or default[0], a.after or default[1]

direct = pd.read_csv(f"results/raw/{before}__{a.test_set}.csv")
multi = pd.read_csv(f"results/raw/{after}__{a.test_set}.csv")
df = direct[["utt_id", "reference", "ref_norm"]].copy()
df["direct"], df["direct_word_err"] = direct.hypothesis, direct.word_err
df["multistage"], df["multistage_word_err"] = multi.hypothesis, multi.word_err

wrong = df[(df.direct_word_err > 0) | (df.multistage_word_err > 0)]
wrong = wrong.sample(min(a.n, len(wrong)), random_state=42).reset_index(drop=True)
for col in ["direct_errors", "multistage_errors", "notes"]:
    wrong[col] = ""

out_dir = f"results/error_analysis/{a.language}_audio"
os.makedirs(out_dir, exist_ok=True)
table = pq.read_table(f"data/test_{a.test_set}_{a.language}.parquet",
                      columns=["utt_id", "audio"]).to_pydict()
audio = dict(zip(table["utt_id"], table["audio"]))
for i, uid in enumerate(wrong.utt_id):
    sf.write(f"{out_dir}/{i:02d}.wav", decode(audio[uid]), 16000)
wrong.insert(0, "clip", [f"{i:02d}.wav" for i in range(len(wrong))])

path = f"results/error_analysis/{a.language}_50.csv"
wrong.insert(1, "runs", f"{before} vs {after}")
wrong.to_csv(path, index=False, encoding="utf-8-sig")   # BOM so Excel shows Indic text
print(f"{len(wrong)} rows -> {path}, audio in {out_dir}/")
