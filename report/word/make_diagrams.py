"""
make_diagrams.py - the two diagrams in the project report (pipeline and system architecture),
drawn in Times for print.

    .venv/bin/python report/word/make_diagrams.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "font.size": 11})
INK, MUTED, HI, EN, LINE, FILL = "#1b1d1a", "#55595e", "#985a0e", "#2a69ac", "#8a8f96", "#f4f2ec"


K = 8.5 / (11 * (21.0 - 3.81 - 2.54) / 2.54 / 10)   # both diagrams are 10 in wide and print at the text width


def box(ax, x, y, w, h, title, sub="", edge=LINE, fill="white", lw=1.3, tsize=11.5, ssize=9.5):
    """Rounded box; title over grey lines, centred as one block. Sizes are scaled to print at about 8.5 pt."""
    tsize, ssize = tsize * K, ssize * K
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec=edge, lw=lw))
    if sub:
        th, gap, sh = tsize / 72 * 1.15, ssize / 72 * 0.45, (sub.count("\n") + 1) * ssize / 72 * 1.25
        top = y + h / 2 + (th + gap + sh) / 2
        ax.text(x + w / 2, top - th / 2, title, ha="center", va="center", fontsize=tsize, fontweight="bold", color=INK)
        ax.text(x + w / 2, top - th - gap, sub, ha="center", va="top", fontsize=ssize, color=MUTED, linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=tsize, fontweight="bold", color=INK)


def arrow(ax, x1, y1, x2, y2, color=MUTED):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, lw=1.2, color=color, shrinkA=0, shrinkB=0))


def pipeline():
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    box(ax, 0.0, 1.7, 1.85, 1.2, "whisper-base", "74M parameters\nfrozen + LoRA")
    box(ax, 2.3, 3.2, 2.1, 1.05, "Hindi pivot", "IndicVoices · 45 h\n2,000 steps · related", edge=HI, lw=1.8)
    box(ax, 2.3, 1.77, 2.1, 1.05, "English pivot", "LibriSpeech · 45 h\n2,000 steps · control", edge=EN, lw=1.8)
    box(ax, 2.3, 0.35, 2.1, 1.05, "No pivot", "direct training")
    box(ax, 5.0, 1.35, 2.3, 1.9, "Target stage", "IndicVoices · 15 h\n1,000 steps\nMarathi, Odia\nor Kannada", edge=INK, lw=1.8, fill=FILL)
    box(ax, 7.85, 1.35, 2.1, 1.9, "Evaluation", "FLEURS + Kathbath\n600 clips each\nWER · CER · script\nbootstrap 95% CI")
    for y in (3.72, 2.3, 0.88):
        arrow(ax, 1.85, 2.3, 2.3, y)
        arrow(ax, 4.4, y, 5.0, 2.3)
    arrow(ax, 7.3, 2.3, 7.85, 2.3)
    fig.savefig(os.path.join(OUT, "fig_pipeline.png"), dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def architecture():
    fig, ax = plt.subplots(figsize=(10, 5.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.0)
    ax.axis("off")
    ax.text(0.05, 4.68, "RESEARCH PIPELINE", fontsize=9 * K, fontweight="bold", color=MUTED)
    top = [("Data sources", "IndicVoices\nLibriSpeech\nFLEURS, Kathbath"), ("Data prep", "seeded shard\nsampling, filters,\nParquet"),
           ("Training", "LoRA on the\nApple M4,\nresumable queue"), ("Evaluation", "normalizer\nWER · CER · script\nbootstrap CIs"),
           ("Results", "results_master\n.csv, tables,\nfigures")]
    bot = [("LoRA adapters", "merged into\nwhisper-base"), ("MLX", "fp16 and 4-bit\nweights"), ("FastAPI server", "localhost,\noffline,\n/api routes"),
           ("Web interface", "React, recorder,\nbench, results"), ("Users", "presenter and\nexaminers")]
    w, h, gap = 1.78, 1.35, 0.25
    for row, (y, items) in enumerate([(3.2, top), (0.75, bot)]):
        for i, (t, sub) in enumerate(items):
            x = 0.05 + i * (w + gap)
            box(ax, x, y, w, h, t, sub, edge=INK if i == 2 else LINE, lw=1.7 if i == 2 else 1.3, fill=FILL if i == 2 else "white", tsize=10.5, ssize=8.6)
            if i:
                arrow(ax, x - gap, y + h / 2, x, y + h / 2)
    ax.text(0.05, 0.42, "DEPLOYMENT AND DEMO", fontsize=9 * K, fontweight="bold", color=MUTED)
    arrow(ax, 0.05 + 2 * (w + gap) + w / 2, 3.2, 0.05 + w / 2, 2.1)
    arrow(ax, 0.05 + 4 * (w + gap) + w / 2, 3.2, 0.05 + 3 * (w + gap) + w / 2, 2.1)
    fig.savefig(os.path.join(OUT, "fig_architecture.png"), dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    pipeline()
    architecture()
    print("wrote", OUT)
