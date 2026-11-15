"""
figures.py - the report's figures, drawn from results/tables (run analysis.py first). Owner: M4.

    python src/figures.py        # writes results/figures/*.png and *.svg

Print palette (light): the two pivot colours validated with the dataviz checks
(Hindi #985a0e, English #2a69ac on white); text in ink, never in series colour.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

OUT = "results/figures"
INK, MUTED, GRID = "#1b1d1a", "#4c4f48", "#e2dfd6"
HINDI, ENGLISH = "#985a0e", "#2a69ac"
TARGETS = [("marathi", "Marathi", "Indo-Aryan · shares Hindi's script"),
           ("odia", "Odia", "Indo-Aryan · own script"),
           ("kannada", "Kannada", "Dravidian · own script")]

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10, "text.color": INK,
    "axes.labelcolor": INK, "axes.edgecolor": GRID, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "figure.dpi": 200, "savefig.bbox": "tight",
})


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(f"{OUT}/{name}.{ext}")
    plt.close(fig)
    print("wrote", f"{OUT}/{name}.png")


def gains():
    """WER points each pivot saves over direct training, 95% bootstrap CI, both test sets."""
    g = pd.read_csv("results/tables/gains.csv")
    g = g[g.metric == "WER"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True, sharex=True)
    for ax, (ts, title) in zip(axes, [("fleurs", "FLEURS"), ("kathbath", "Kathbath")]):
        for i, (lang, name, _) in enumerate(TARGETS):
            for k, (gain, colour, label) in enumerate([("hindi_pivot_gain", HINDI, "Hindi pivot"),
                                                       ("english_pivot_gain", ENGLISH, "English pivot")]):
                r = g[(g.language == lang) & (g.test_set == ts) & (g.gain == gain)]
                if r.empty or pd.isna(r.points.iloc[0]):
                    continue
                r = r.iloc[0]
                y = i + (-0.14 if k == 0 else 0.14)
                ax.plot([r.ci_low, r.ci_high], [y, y], color=colour, lw=2, solid_capstyle="round")
                ax.plot(r.points, y, "o", ms=7, color=colour, mec="white", mew=1.5,
                        label=label if i == 0 else None)
                ax.annotate(f"{r.points:+.1f}", (r.ci_high, y), xytext=(5, 0), textcoords="offset points",
                            va="center", fontsize=8.5, color=INK)
        ax.axvline(0, color=MUTED, lw=1)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.set_title(title, loc="left", fontsize=10.5, fontweight="bold")
        ax.set_xlabel("WER points saved over direct training")
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(range(len(TARGETS)), [f"{n}\n{d}" for _, n, d in TARGETS], fontsize=9)
    axes[0].invert_yaxis()
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.6, -0.14),
               ncol=2, frameon=False, fontsize=9)
    fig.suptitle("Equal-size pivots: Hindi helps, English does not (dot: gain; line: 95% CI)",
                 x=0.02, y=1.04, ha="left", fontsize=11, fontweight="bold")
    save(fig, "fig_gains")


def fertility():
    f = pd.read_csv("results/tables/fertility.csv").set_index("language")
    order = ["hindi", "marathi", "kannada", "odia"]
    fig, ax = plt.subplots(figsize=(4.6, 2.4))
    vals = [f.loc[l, "tokens_per_char"] for l in order]
    ax.barh(range(4), vals, height=0.42, color=[MUTED, MUTED, MUTED, INK])
    for i, v in enumerate(vals):
        ax.text(v + 0.04, i, f"{v:.2f}", va="center", fontsize=9, color=INK)
    ax.set_yticks(range(4), [l.title() for l in order])
    ax.invert_yaxis()
    ax.set_xlabel("Whisper tokens per letter (FLEURS references)")
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    save(fig, "fig_fertility")


def wer_by_method():
    """Absolute WER per language and method, FLEURS: the context for the gains."""
    m = pd.read_csv("results/results_master.csv")
    m = m[m.test_set == "fleurs"]
    runs = [("Zero-shot", lambda l: f"Z-{l}-bengali" if l == "odia" else f"Z-{l}", "#a6aea8"),
            ("Direct", lambda l: f"D-{l}", MUTED),
            ("Hindi → target", lambda l: f"H-{l}", HINDI),
            ("English → target", lambda l: f"E-{l}", ENGLISH)]
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    for i, (lang, name, _) in enumerate(TARGETS):
        for k, (label, rid, colour) in enumerate(runs):
            r = m[m.run_id == rid(lang)]
            if r.empty:
                continue
            ax.plot(r.WER_clean.iloc[0], i, "o", ms=8, color=colour, mec="white", mew=1.5,
                    label=label if i == 0 else None)
    ax.set_yticks(range(len(TARGETS)), [n for _, n, _ in TARGETS])
    ax.invert_yaxis()
    ax.set_xlabel("WER % on FLEURS (lower is better)")
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=4, frameon=False, fontsize=8.5)
    save(fig, "fig_wer_by_method")


if __name__ == "__main__":
    gains()
    fertility()
    wer_by_method()
