"""
experiments.py - the experiment grid, in the order the queue runs it.

Science-critical runs come first, stretch runs last, so if time runs out
we lose the least important rows.
"""
import json

from langs import ODIA_MAIN_TOKEN, ODIA_TOKENS, TARGETS

PIVOT_HOURS, TARGET_HOURS = 45, 15
TEST_SETS = ["fleurs", "kathbath"]


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


def odia_token():
    return ODIA_MAIN_TOKEN


def token_for(language):
    return odia_token() if language == "odia" else language


def runs():
    R = []
    # Zero-shot: the "before" numbers, and the Odia token study (RQ2)
    for lang in ["hindi"] + TARGETS:
        tokens = ODIA_TOKENS if lang == "odia" else [lang]
        for tok in tokens:
            R.append({"id": f"Z-{lang}" + (f"-{tok}" if lang == "odia" else ""),
                      "kind": "eval", "language": lang, "token": tok,
                      "method": "zeroshot", "pivot": "none"})

    # Hindi pivot; nothing builds on it until it beats zero-shot Hindi
    R.append({"id": "P-hindi", "kind": "train", "language": "hindi", "token": "hindi",
              "data": f"train_hindi_{PIVOT_HOURS}h", "steps": "pivot_steps",
              "method": "pivot", "pivot": "none", "gate": "Z-hindi"})
    for lang in TARGETS:                                   # pivot-only transfer
        R.append({"id": f"X-hindi-{lang}", "kind": "eval", "language": lang,
                  "token": "auto", "adapter": "P-hindi",
                  "method": "pivot_transfer", "pivot": "hindi"})

    for prefix, method, init, pivot in [("D", "direct_lora", None, "none"),
                                        ("H", "multistage_lora", "P-hindi", "hindi")]:
        for lang in TARGETS:
            R.append({"id": f"{prefix}-{lang}", "kind": "train", "language": lang,
                      "token": "auto", "data": f"train_{lang}_{TARGET_HOURS}h",
                      "steps": "target_steps", "init": init,
                      "method": method, "pivot": pivot})

    # English pivot: same hours and steps, related to none of the targets
    R.append({"id": "P-english", "kind": "train", "language": "english", "token": "english",
              "data": f"train_english_{PIVOT_HOURS}h", "steps": "pivot_steps",
              "method": "pivot", "pivot": "none", "no_eval": True})
    for lang in TARGETS:
        R.append({"id": f"E-{lang}", "kind": "train", "language": lang, "token": "auto",
                  "data": f"train_{lang}_{TARGET_HOURS}h", "steps": "target_steps",
                  "init": "P-english", "method": "multistage_lora", "pivot": "english"})
    for lang in TARGETS:
        R.append({"id": f"X-english-{lang}", "kind": "eval", "language": lang,
                  "token": "auto", "adapter": "P-english",
                  "method": "pivot_transfer", "pivot": "english"})

    # Stretch: Odia direct with the other two borrowed tokens (RQ2 after
    # training; D-odia is the bengali row)
    for tok in ODIA_TOKENS:
        if tok != ODIA_MAIN_TOKEN:
            R.append({"id": f"T-odia-{tok}", "kind": "train", "language": "odia",
                      "token": tok, "data": f"train_odia_{TARGET_HOURS}h",
                      "steps": "target_steps", "method": "direct_lora", "pivot": "none"})
    return R
