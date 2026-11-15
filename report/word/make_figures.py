"""
make_figures.py - every chart and diagram in the project report, drawn from the project's files
(results/, data/, runs/*/train_log.jsonl, config.json, report/slides/tokens_cache.json).

    .venv/bin/python report/word/make_figures.py      # writes report/word/figures/*.png
"""
import csv
import json
import os

import matplotlib
import matplotlib.text

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "report", "word", "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "font.size": 10.5,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#888888",
                     "axes.titlesize": 11.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
                     "xtick.color": "#333333", "ytick.color": "#333333", "legend.frameon": False})
INK, MUTED, GRID, FILL = "#1b1d1a", "#55595e", "#dcdad3", "#f4f2ec"
ZS, DIR, HI, EN, BAD = "#a6aea8", "#4c4f48", "#985a0e", "#2a69ac", "#b02a1e"
NAME = {"hindi": "Hindi", "marathi": "Marathi", "kannada": "Kannada", "odia": "Odia"}
TARGETS = ["marathi", "odia", "kannada"]


def rows(p):
    with open(os.path.join(ROOT, p), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


master = rows("results/results_master.csv")
gains = rows("results/tables/gains.csv")
deploy = rows("results/tables/deployment.csv")
fert = {r["language"]: r for r in rows("results/tables/fertility.csv")}


def M(run, ts="fleurs", col="WER_clean"):
    return float(next(r for r in master if r["run_id"] == run and r["test_set"] == ts)[col])


def G(lang, ts, key, metric="WER"):
    r = next(r for r in gains if r["language"] == lang and r["test_set"] == ts and r["gain"] == key and r["metric"] == metric)
    return float(r["points"]), float(r["ci_low"]), float(r["ci_high"])


def log(run):
    return [json.loads(l) for l in open(os.path.join(ROOT, "runs", run, "train_log.jsonl"))]


TEXT_W = 21.0 - 3.81 - 2.54   # cm, the report's text width
PLACE = {"fig_drops": 13.5, "fig_bench": 13.5, "fig_loss_pivots": 13.0, "fig_script": 13.5, "fig_delta": 13.0,
         "fig_pivot_only": 13.5, "fig_fertility": 10.5, "fig_odia_tokens": 12.5}   # printed width in cm; others: TEXT_W
PRINT_PT = 8.5                 # smallest normal text size wanted on paper


def print_scale(fig, name, base=10.5):
    """Enlarge every text in the figure so it prints at about PRINT_PT at the width the report places it."""
    s = PLACE.get(name, TEXT_W) / 2.54 / fig.get_size_inches()[0]
    k = max(1.0, PRINT_PT / (base * s))
    for t in fig.findobj(matplotlib.text.Text):
        t.set_fontsize(t.get_fontsize() * k)
    if len(fig.axes) > 1 and all(ax.axison for ax in fig.axes):
        fig.tight_layout()


def fixed_scale(fig, name, base=10.5):
    """The text factor print_scale would apply; diagrams draw at final sizes so text fits its boxes."""
    s = PLACE.get(name, TEXT_W) / 2.54 / fig.get_size_inches()[0]
    return max(1.0, PRINT_PT / (base * s))


def save(fig, name, scale=True):
    if scale:
        print_scale(fig, name)
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)


def grid_y(ax):
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)


def label_bars(ax, bars, fmt="{:.1f}", size=8.5, color=INK, inside=False):
    from decimal import ROUND_HALF_UP, Decimal
    for b in bars:
        h = b.get_height()
        if h != h:  # NaN: no bar
            continue
        q = Decimal(repr(float(h))).quantize(Decimal("0.1") if "1f" in fmt else Decimal("1"), rounding=ROUND_HALF_UP)
        ax.annotate(str(q), (b.get_x() + b.get_width() / 2, h), xytext=(0, 2), textcoords="offset points",
                    ha="center", va="bottom", fontsize=size, color=color)


# ---------------------------------------------------------------- diagrams
def box(ax, x, y, w, h, title, sub="", edge="#8a8f96", fill="white", lw=1.3, tsize=11.5, ssize=9.5):
    """A rounded box with a bold title over grey lines, centred as one block. Axis units must be inches."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec=edge, lw=lw))
    if sub:
        th, gap, sh = tsize / 72 * 1.15, ssize / 72 * 0.45, (sub.count("\n") + 1) * ssize / 72 * 1.25
        top = y + h / 2 + (th + gap + sh) / 2
        ax.text(x + w / 2, top - th / 2, title, ha="center", va="center", fontsize=tsize, fontweight="bold", color=INK)
        ax.text(x + w / 2, top - th - gap, sub, ha="center", va="top", fontsize=ssize, color=MUTED, linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=tsize, fontweight="bold", color=INK)


def arrow(ax, x1, y1, x2, y2, color=MUTED, style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=12, lw=1.2, color=color, shrinkA=0, shrinkB=0))


def lora_diagram():
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    ax.set_xlim(0, 8.5)
    ax.set_ylim(0, 3.4)
    ax.axis("off")
    K = fixed_scale(fig, "fig_lora")
    T, U = 11.5 * K, 9.5 * K
    box(ax, 0.1, 1.2, 1.3, 1.2, "Input x", "d_in features", tsize=T, ssize=U)
    box(ax, 2.0, 2.05, 2.6, 1.25, "$W_0$  (frozen)", "pre-trained query / value\nprojection, not updated", edge=DIR, fill="#ecebe6", tsize=T, ssize=U)
    box(ax, 2.0, 0.15, 1.15, 1.25, "A", f"r × k\nr = 32", edge=HI, lw=1.8, tsize=T, ssize=U)
    box(ax, 3.45, 0.15, 1.15, 1.25, "B", "d × r\ntrained", edge=HI, lw=1.8, tsize=T, ssize=U)
    ax.add_patch(plt.Circle((5.55, 1.8), 0.28, fc="white", ec=INK, lw=1.3))
    ax.text(5.55, 1.8, "+", ha="center", va="center", fontsize=16 * K, color=INK)
    box(ax, 6.45, 1.15, 1.95, 1.3, "Output h", "$h = W_0x$\n$+\\ (\\alpha/r)\\,BAx$", tsize=T, ssize=U)
    arrow(ax, 1.4, 1.8, 2.0, 2.65)
    arrow(ax, 1.4, 1.8, 2.0, 0.8)
    arrow(ax, 3.15, 0.8, 3.45, 0.8)
    arrow(ax, 4.6, 2.65, 5.33, 1.95)
    arrow(ax, 4.6, 0.8, 5.33, 1.65)
    ax.text(4.85, 0.95, "× α/r = 2", fontsize=9.5 * K, color=HI)
    arrow(ax, 5.83, 1.8, 6.45, 1.8)
    save(fig, "fig_lora", scale=False)


def dataprep_diagram():
    fig, ax = plt.subplots(figsize=(10, 2.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.3)
    ax.axis("off")
    K = fixed_scale(fig, "fig_dataprep")
    steps = [("Corpus shards", "IndicVoices:\n36–59 GB per\nlanguage;\nLibriSpeech\nclean-100"),
             ("Seeded sample", "shards spread\nacross the\ncorpus, seed 42;\nduration from\nmetadata"),
             ("Filters", "2–30 s clips\nno tagged rows\n≤50 clips per\nspeaker; labels\n≤443 tokens"),
             ("Hour budget", "Hindi, English:\n45 h each\nMarathi, Odia,\nKannada:\n15 h each"),
             ("Parquet, stats", "audio bytes,\ntext, speaker;\nJSON record\nof every drop")]
    w, gap = 1.78, 0.25
    for i, (t, s) in enumerate(steps):
        x = 0.05 + i * (w + gap)
        box(ax, x, 0.1, w, 2.1, t, s, edge=INK if i == 2 else "#8a8f96", lw=1.7 if i == 2 else 1.3, fill=FILL if i == 2 else "white",
            tsize=10 * K, ssize=8.3 * K)
        if i:
            arrow(ax, x - gap, 1.15, x, 1.15)
    save(fig, "fig_dataprep", scale=False)


def odia_bytes():
    tok = json.load(open(os.path.join(ROOT, "report/slides/tokens_cache.json")))
    toks = tok["tokens"]
    per_row = 16
    n_rows = (len(toks) + per_row - 1) // per_row
    fig, ax = plt.subplots(figsize=(10, 0.5 * n_rows))
    ax.set_xlim(0, per_row)
    ax.set_ylim(-n_rows, 0)
    ax.axis("off")
    for i, t in enumerate(toks):
        r, c = divmod(i, per_row)
        space = (t["text"] or "") == " "
        ax.add_patch(FancyBboxPatch((c + 0.06, -r - 0.82), 0.88, 0.7, boxstyle="round,pad=0,rounding_size=0.12",
                                    fc="white" if space else "#efede6", ec=HI if space else "#c9c5b9", lw=1.4 if space else 0.8))
        ax.text(c + 0.5, -r - 0.47, "space" if space else t["hex"], ha="center", va="center",
                fontsize=7.5 if space else 8.5 if len(t["hex"]) <= 2 else 5.5,
                color=HI if space else MUTED, family="monospace", fontweight="bold" if space else "normal")
    save(fig, "fig_odia_bytes")


def gantt():
    tasks = [("Literature survey, research gap, design (Review 1)", 0, 1), ("Benchmark the M4; choose whisper-base", 1, 1.35),
             ("Data preparation (5 corpora, 2 test sets)", 1.1, 1.8), ("Zero-shot baselines", 1.5, 1.95),
             ("Hindi pivot and gate", 1.8, 2.25), ("Direct and Hindi → target runs", 2.2, 2.6), ("English pivot and control runs", 2.5, 2.85),
             ("Odia token and pivot-only runs", 2.75, 3.05), ("Analysis, confidence intervals, figures", 2.9, 3.4),
             ("MLX deployment and demo application", 2.8, 3.5), ("IEEE paper, presentation, report", 3.2, 4.0)]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for i, (t, a, b) in enumerate(tasks):
        ax.barh(i, b - a, left=a, height=0.55, color=DIR if a < 1 else HI, alpha=0.9)
    ax.set_yticks(range(len(tasks)), [t for t, _, _ in tasks], fontsize=9.5)
    ax.invert_yaxis()
    ax.set_xticks([0.5, 1.5, 2.5, 3.5], ["Aug 2026\n(Review 1)", "Mon 2 Nov", "Tue 3 Nov", "Wed 4 Nov"])
    for x in (1, 2, 3):
        ax.axvline(x, color=GRID, lw=0.8)
    ax.set_xlim(0, 4)
    ax.tick_params(axis="y", length=0)
    save(fig, "fig_gantt")


# ---------------------------------------------------------------- charts
def wer_methods():
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, ts in zip(axes, ["fleurs", "kathbath"]):
        x = range(len(TARGETS))
        for k, (pre, lab, col) in enumerate([("D", "Direct", DIR), ("H", "Hindi → target", HI), ("E", "English → target", EN)]):
            vals = [M(f"{pre}-{t}", ts) for t in TARGETS]
            bars = ax.bar([i + (k - 1) * 0.26 for i in x], vals, width=0.25, color=col, label=lab)
            label_bars(ax, bars, size=8)
        ax.set_xticks(list(x), [NAME[t] for t in TARGETS])
        ax.set_ylim(50, 80)
        ax.set_title("FLEURS" if ts == "fleurs" else "Kathbath")
        grid_y(ax)
    axes[0].set_ylabel("WER (%)")
    axes[0].legend(loc="upper left", fontsize=9, ncol=3, bbox_to_anchor=(0, -0.12))
    save(fig, "fig_wer_methods")


def loss_pivots():
    fig, ax = plt.subplots(figsize=(8, 3.3))
    for run, lab, col in [("P-hindi", "Hindi pivot (IndicVoices, 45 h)", HI), ("P-english", "English pivot (LibriSpeech, 45 h)", EN)]:
        L = log(run)
        ax.plot([r["step"] for r in L], [r["loss"] for r in L], color=col, lw=1.8, label=lab)
    ax.set_xlabel("Training step")
    ax.set_ylabel("Training loss")
    ax.legend(fontsize=9.5)
    grid_y(ax)
    save(fig, "fig_loss_pivots")


def loss_targets():
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
    for ax, t in zip(axes, TARGETS):
        for pre, lab, col in [("D", "Direct", DIR), ("H", "Hindi → target", HI), ("E", "English → target", EN)]:
            L = log(f"{pre}-{t}")
            ax.plot([r["step"] for r in L], [r["loss"] for r in L], color=col, lw=1.6, label=lab)
        ax.set_title(NAME[t])
        ax.set_xlabel("Step")
        grid_y(ax)
    axes[0].set_ylabel("Training loss")
    axes[0].legend(fontsize=9, loc="upper right")
    save(fig, "fig_loss_targets")


def script_validity():
    langs = ["hindi", "marathi", "odia", "kannada"]
    zs = [M("Z-odia-bengali" if l == "odia" else f"Z-{l}", "fleurs", "script_valid") for l in langs]
    po = [float("nan") if l == "hindi" else M(f"X-hindi-{l}", "fleurs", "script_valid") for l in langs]
    tr = [M("P-hindi", "fleurs", "script_valid") if l == "hindi" else M(f"H-{l}", "fleurs", "script_valid") for l in langs]
    fig, ax = plt.subplots(figsize=(9, 3.3))
    for k, (vals, lab, col) in enumerate([(zs, "Untrained whisper-base", ZS), (po, "Hindi pivot only (targets)", HI), (tr, "After target training", DIR)]):
        bars = ax.bar([i + (k - 1) * 0.26 for i in range(4)], vals, width=0.25, color=col, label=lab)
        label_bars(ax, bars, "{:.0f}", size=8)
    ax.set_xticks(range(4), [NAME[l] for l in langs])
    ax.set_ylabel("Letters in the right script (%)")
    ax.set_ylim(0, 115)
    ax.legend(fontsize=9, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.1))
    grid_y(ax)
    save(fig, "fig_script")


def pivot_only():
    fig, ax = plt.subplots(figsize=(9, 3.3))
    for k, (pre, lab, col) in enumerate([("Z", "Untrained", ZS), ("X-hindi", "Hindi pivot only", HI), ("X-english", "English pivot only", EN)]):
        vals = [M(("Z-odia-bengali" if t == "odia" else f"Z-{t}") if pre == "Z" else f"{pre}-{t}", "fleurs", "CER_clean") for t in TARGETS]
        bars = ax.bar([i + (k - 1) * 0.26 for i in range(3)], vals, width=0.25, color=col, label=lab)
        label_bars(ax, bars, size=8)
    ax.set_xticks(range(3), [NAME[t] for t in TARGETS])
    ax.set_ylabel("CER on FLEURS (%)")
    ax.legend(fontsize=9, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.1))
    grid_y(ax)
    save(fig, "fig_pivot_only")


def delta_chart():
    fig, ax = plt.subplots(figsize=(8.5, 3.3))
    for k, (ts, col, lab) in enumerate([("fleurs", HI, "FLEURS"), ("kathbath", "#c9972c", "Kathbath")]):
        for i, t in enumerate(TARGETS):
            p, lo, hi = G(t, ts, "hindi_specific")
            x = i + (k - 0.5) * 0.3
            ax.bar(x, p, width=0.28, color=col, label=lab if i == 0 else None)
            ax.plot([x, x], [lo, hi], color=INK, lw=1.2)
            ax.plot([x - 0.05, x + 0.05], [lo, lo], color=INK, lw=1.2)
            ax.plot([x - 0.05, x + 0.05], [hi, hi], color=INK, lw=1.2)
            ax.text(x, hi + 0.15, f"+{p:.1f}", ha="center", fontsize=8.5)
    ax.axhline(0, color=MUTED, lw=1)
    ax.set_xticks(range(3), [NAME[t] for t in TARGETS])
    ax.set_ylabel("Δ = Hindi gain − English gain\n(WER points)")
    ax.legend(fontsize=9)
    grid_y(ax)
    save(fig, "fig_delta")


def odia_tokens():
    fig, ax = plt.subplots(figsize=(8, 3.2))
    toks = [("Bengali", "D-odia"), ("Assamese", "T-odia-assamese"), ("Hindi", "T-odia-hindi")]
    for k, (ts, col) in enumerate([("fleurs", HI), ("kathbath", "#c9972c")]):
        bars = ax.bar([i + (k - 0.5) * 0.3 for i in range(3)], [M(r, ts) for _, r in toks], width=0.28, color=col,
                      label="FLEURS" if ts == "fleurs" else "Kathbath")
        label_bars(ax, bars, size=8.5)
    ax.set_xticks(range(3), [f"<|{c}|> {n}" for (n, _), c in zip(toks, ["bn", "as", "hi"])])
    ax.set_ylim(55, 80)
    ax.set_ylabel("Odia WER after training (%)")
    ax.legend(fontsize=9)
    grid_y(ax)
    save(fig, "fig_odia_tokens")


def norm_chart():
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
    for ax, ts in zip(axes, ["fleurs", "kathbath"]):
        for k, (col_, lab, c) in enumerate([("WER_raw", "Raw", ZS), ("WER_clean", "Our normalizer", DIR), ("WER_whisper_norm", "Whisper's normalizer", BAD)]):
            bars = ax.bar([i + (k - 1) * 0.26 for i in range(3)], [M(f"H-{t}", ts, col_) for t in TARGETS], width=0.25, color=c, label=lab)
            label_bars(ax, bars, size=8)
        ax.set_xticks(range(3), [NAME[t] for t in TARGETS])
        ax.set_title("FLEURS" if ts == "fleurs" else "Kathbath")
        grid_y(ax)
    axes[0].set_ylabel("WER of the Hindi-pivot model (%)")
    axes[0].legend(fontsize=9, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.1))
    save(fig, "fig_norm")


def deploy_chart():
    order = [("P-hindi", "Hindi\npivot"), ("H-marathi", "Hi →\nMarathi"), ("H-odia", "Hi →\nOdia"), ("H-kannada", "Hi →\nKannada")]
    d = {(r["run_id"], r["precision"]): r for r in deploy}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
    for ax, metric in zip(axes, ["WER", "CER"]):
        for k, (pr, lab, col) in enumerate([("fp16", "fp16 (144 MB)", DIR), ("q4", "4-bit (42 MB)", BAD)]):
            bars = ax.bar([i + (k - 0.5) * 0.4 for i in range(4)], [float(d[(r, pr)][metric]) for r, _ in order], width=0.38, color=col, label=lab)
            label_bars(ax, bars, size=6.8)
        ref = [float(d[(r, "fp16")][f"{metric}_pytorch_same_clips"]) for r, _ in order]
        ax.scatter(range(4), ref, marker="_", s=500, color=HI, zorder=3, label="PyTorch, same clips", linewidths=2)
        ax.set_xticks(range(4), [n for _, n in order], fontsize=9)
        ax.set_title(f"{metric} on 100 FLEURS clips")
        grid_y(ax)
    axes[0].set_ylabel("%")
    axes[0].legend(fontsize=9, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.2))
    save(fig, "fig_deploy")


def bench_chart():
    b = json.load(open(os.path.join(ROOT, "config.json")))["bench"]
    rows_ = [(f"whisper-small · batch {r['batch']} · {r['precision']}{' · checkpointing' if r['grad_ckpt'] else ''}", r["samples_per_sec"], ZS)
             for r in b["train"] if "samples_per_sec" in r]
    rows_ += [(f"whisper-base · batch {r['batch']} · {r['precision']} · {r['attn']}", r["clips_per_sec"], HI if (r["attn"] == "eager" and r["precision"] == "fp32" and r["batch"] == 4) else DIR)
              for r in b["whisper_base_attention"]]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    y = range(len(rows_))
    bars = ax.barh(list(y), [v for _, v, _ in rows_], color=[c for _, _, c in rows_], height=0.6)
    for bar, (_, v, _) in zip(bars, rows_):
        ax.text(v + 0.06, bar.get_y() + bar.get_height() / 2, f"{v:.2f}", va="center", fontsize=8.5)
    ax.set_yticks(list(y), [n for n, _, _ in rows_], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Training throughput on the Apple M4 (clips per second)")
    ax.grid(axis="x", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    save(fig, "fig_bench")


def drops_chart():
    langs = [("train_hindi_45h", "Hindi"), ("train_marathi_15h", "Marathi"), ("train_odia_15h", "Odia"), ("train_kannada_15h", "Kannada")]
    reasons = [("duration", "Outside 2–30 s", ZS), ("tagged", "Annotation tags", DIR), ("label_too_long", "Label over 443 tokens", BAD),
               ("speaker_cap", "Speaker cap", "#c9972c"), ("empty_text", "Empty text", EN)]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    left = [0] * len(langs)
    for key, lab, col in reasons:
        vals = [json.load(open(os.path.join(ROOT, f"data/{n}.json")))["dropped"].get(key, 0) for n, _ in langs]
        ax.barh(range(len(langs)), vals, left=left, color=col, label=lab, height=0.55)
        left = [a + b for a, b in zip(left, vals)]
    for i, v in enumerate(left):
        ax.text(v + 60, i, f"{v:,}", va="center", fontsize=8.5)
    ax.set_yticks(range(len(langs)), [n for _, n in langs])
    ax.invert_yaxis()
    ax.set_xlabel("Clips removed from the sampled shards")
    ax.legend(fontsize=8.5, ncol=5, loc="upper left", bbox_to_anchor=(0, -0.2))
    ax.grid(axis="x", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    save(fig, "fig_drops")


def fertility():
    langs = ["hindi", "marathi", "kannada", "odia"]
    vals = [float(fert[l]["tokens_per_char"]) for l in langs]
    fig, ax = plt.subplots(figsize=(7.5, 2.6))
    bars = ax.barh(range(4), vals, height=0.55, color=[DIR, DIR, DIR, HI])
    for b, v in zip(bars, vals):
        ax.text(v + 0.04, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontsize=9.5)
    ax.set_yticks(range(4), [NAME[l] for l in langs])
    ax.invert_yaxis()
    ax.set_xlabel("Whisper tokens per letter (FLEURS references)")
    ax.grid(axis="x", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    save(fig, "fig_fertility")


if __name__ == "__main__":
    for f in (lora_diagram, dataprep_diagram, odia_bytes, gantt, wer_methods, loss_pivots, loss_targets, script_validity,
              pivot_only, delta_chart, odia_tokens, norm_chart, deploy_chart, bench_chart, drops_chart, fertility):
        f()
