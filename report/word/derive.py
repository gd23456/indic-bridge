"""derive.py - numbers the report needs that come from the statistics code (bootstrap CIs) and the
environment (library versions). Writes report/word/derived.json.

    PYTHONPATH=src .venv/bin/python report/word/derive.py
"""
import importlib.metadata as md
import json
import os
import platform

from analysis import ci, gain_samples

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
out = {"token_diff": {}, "versions": {}}
for other in ["T-odia-assamese", "T-odia-hindi"]:
    for ts in ["fleurs", "kathbath"]:
        s, p = gain_samples("D-odia", other, ts, "word")  # WER(Bengali) - WER(other): positive = other token better
        lo, hi = ci(s)
        out["token_diff"][f"{other}|{ts}"] = [round(float(p), 2), float(lo), float(hi)]
for pkg in ["torch", "transformers", "peft", "datasets", "pyarrow", "pandas", "numpy", "jiwer", "soundfile", "librosa",
            "mlx", "mlx-whisper", "fastapi", "matplotlib", "safetensors"]:
    try:
        out["versions"][pkg] = md.version(pkg)
    except md.PackageNotFoundError:
        out["versions"][pkg] = None
out["versions"]["python"] = platform.python_version()
json.dump(out, open("report/word/derived.json", "w"), indent=1)
print(json.dumps(out, indent=1))
