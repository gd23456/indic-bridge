"""page_map.py - read the rendered report (one text per PDF page) and write pages.json: the printed
page number of every contents entry, figure and table, for the second build pass.

    python3 report/word/page_map.py pages_text.json report/word/pages.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
pages = [re.sub(r"\s+", " ", p) for p in json.load(open(sys.argv[1]))]
plan = json.load(open(os.path.join(HERE, "toc_plan.json")))
caps = json.load(open(os.path.join(HERE, "captions.json")))


def first_line(p):
    return p.strip()[:60]


def roman(n):
    out = ""
    for v, s in [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]:
        while n >= v:
            out, n = out + s, n - v
    return out


abstract = next(i for i, p in enumerate(pages) if p.strip().startswith("ABSTRACT"))
ch1 = next(i for i, p in enumerate(pages) if p.strip().startswith("CHAPTER 1 INTRODUCTION"))
out = {}
for key, head in [("front:contents", "CONTENTS"), ("front:lof", "LIST OF FIGURES"), ("front:lot", "LIST OF TABLES"), ("front:acr", "LIST OF ACRONYMS")]:
    i = next(i for i in range(abstract, ch1) if pages[i].strip().startswith(head))
    out[key] = roman(i - abstract + 1)
missing = []
for level, text, key in plan:
    if key.startswith("ch:"):
        n = key.split(":")[1]
        needle = f"CHAPTER {n} "
        hit = next((i for i in range(ch1, len(pages)) if pages[i].strip().startswith(needle)), None)
    elif key == "refs":
        hit = next((i for i in range(ch1, len(pages)) if pages[i].strip().startswith("REFERENCES")), None)
    elif key == "app":
        hit = next((i for i in range(ch1, len(pages)) if pages[i].strip().startswith("APPENDICES")), None)
    else:
        hit = next((i for i in range(ch1, len(pages)) if text in pages[i]), None)
    if hit is None:
        missing.append(text)
    else:
        out[key] = str(hit - ch1 + 1)
for kind, word in (("figs", "Fig."), ("tabs", "Table")):
    for num, title, label in caps[kind]:
        needle = f"{word} {num}:"
        hit = next((i for i in range(ch1, len(pages)) if needle in pages[i]), None)
        if hit is None:
            missing.append(needle)
        else:
            out[label] = str(hit - ch1 + 1)
# a table caption with no table after it on the same page: the next build starts that block on a new page
prev = json.load(open(sys.argv[2])).get("_breaks", []) if os.path.exists(sys.argv[2]) else []
breaks = set(prev)
for num, title, label in caps["tabs"]:
    needle = f"Table {num}:"
    i = next((i for i in range(ch1, len(pages)) if needle in pages[i]), None)
    if i is not None:
        rest = pages[i][pages[i].index(needle) + len(needle):].strip()
        if len(rest) < len(title) + 12:
            breaks.add(label)
out["_breaks"] = sorted(breaks)
new = sorted(breaks - set(prev))
json.dump(out, open(sys.argv[2], "w"), indent=0)
print("stranded captions:", new)
print(f"{len(out)} page numbers; abstract=pdf page {abstract + 1}, chapter 1=pdf page {ch1 + 1}, total pdf pages {len(pages)}")
print("missing:", missing)
