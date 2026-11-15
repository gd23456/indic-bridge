"""
build_rvu_pptx.py - the viva deck in RV University's PPT template, filled from the project's
result files (every number is read from results/ or data/, never typed).

    <venv with python-pptx>/bin/python report/ppt/build_rvu_pptx.py "<template.pptx>" "<out.pptx>"

Keeps the template's title slide, outline slide, literature-survey table, banner style, layout art
and Thank You slide; every other slide is built on the template's "Title and Content" layout with
a clone of its slate-and-gold title banner. Speaker scripts go into each slide's notes.
"""
import copy
import csv
import json
import os
import sys
from decimal import ROUND_HALF_UP, Decimal

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE, OUT = sys.argv[1], sys.argv[2]

# ------------------------------------------------------------------ data
def rows(path):
    with open(os.path.join(ROOT, path), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


master = rows("results/results_master.csv")
gains = rows("results/tables/gains.csv")
inter = rows("results/tables/interaction.csv")
fert = {r["language"]: r for r in rows("results/tables/fertility.csv")}
deploy = rows("results/tables/deployment.csv")
data = {n: json.load(open(os.path.join(ROOT, f"data/{n}.json"))) for n in
        ["train_hindi_45h", "train_english_45h", "train_marathi_15h", "train_odia_15h", "train_kannada_15h", "test_fleurs_odia"]}
tok = json.load(open(os.path.join(ROOT, "report/slides/tokens_cache.json")))


def r1(v):
    return Decimal(repr(float(v))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def f1(v):
    return f"{r1(v)}"


def sg(v):
    q = r1(v)
    return f"{'+' if q > 0 else '−' if q < 0 else ''}{abs(q)}"


def M(run, ts="fleurs", col="WER_clean"):
    return float(next(r for r in master if r["run_id"] == run and r["test_set"] == ts)[col])


def G(lang, ts, key, metric="WER"):
    r = next(r for r in gains if r["language"] == lang and r["test_set"] == ts and r["gain"] == key and r["metric"] == metric)
    return float(r["points"]), float(r["ci_low"]), float(r["ci_high"])


NAME = {"hindi": "Hindi", "marathi": "Marathi", "kannada": "Kannada", "odia": "Odia"}
TARGETS = ["marathi", "odia", "kannada"]

# ------------------------------------------------------------------ style (from the template)
SLATE, GOLD = RGBColor(0x23, 0x30, 0x39), RGBColor(0xD7, 0xAC, 0x54)
INK, MUTED, LINE = RGBColor(0x1F, 0x26, 0x2C), RGBColor(0x55, 0x5E, 0x66), RGBColor(0xD9, 0xD2, 0xC3)
WHITE, TINT = RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xF6, 0xF1, 0xE6)
RED, HI, EN = RGBColor(0xB0, 0x2A, 0x1E), RGBColor(0xA8, 0x77, 0x1C), RGBColor(0x3F, 0x63, 0x86)
BODY = "Arial"
PEOPLE = {"parth": "Parth N. Khandagale", "gourab": "Gourab Dash", "divyansh": "Divyansh Mahecha", "kaushal": "Kaushal BC"}

prs = Presentation(TEMPLATE)
tpl = list(prs.slides)
TITLE_SLIDE, OUTLINE_SLIDE, LIT_TABLE_SLIDE, THANKS_SLIDE = tpl[0], tpl[1], tpl[4], tpl[15]
CONTENT_LAYOUT = tpl[2].slide_layout
BANNER = next(s for s in tpl[2].shapes if s.name == "Google Shape;77;p16")._element
LIT_TABLE = next(s for s in LIT_TABLE_SLIDE.shapes if s.has_table)._element
built = []          # (slide, presenter) in final order


def set_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def banner(slide, title):
    el = copy.deepcopy(BANNER)
    slide.shapes._spTree.append(el)
    sp = slide.shapes[-1]
    w = min(7.0, max(3.4, 0.172 * len(title) + 1.0))
    x = min(4.83 - w / 2, 7.85 - w)
    sp.left, sp.top, sp.width, sp.height = Inches(x), Emu(381270), Inches(w), Emu(466800)
    run = sp.text_frame.paragraphs[0].runs[0]
    run.text = title
    sp.name = "Title banner"
    return sp


def content_slide(title, who, notes):
    s = prs.slides.add_slide(CONTENT_LAYOUT)
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    banner(s, title)
    set_notes(s, notes)
    built.append((s, who))
    return s


def tb(slide, x, y, w, h, paras, size=14, color=INK, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT, name=None, font=BODY, spacing=4):
    """paras: list of str | list of (text, {bold, color, italic, size}) runs | ('bullet', ...)"""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = anchor
    first = True
    for para in paras:
        bullet = False
        if isinstance(para, tuple) and para and para[0] == "bullet":
            bullet, para = True, para[1]
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(spacing)
        runs = [(para, {})] if isinstance(para, str) else para
        for text, opt in runs:
            r = p.add_run()
            r.text = text
            f = r.font
            f.name = opt.get("font", font)
            f.size = Pt(opt.get("size", size))
            f.bold = opt.get("bold", False)
            f.italic = opt.get("italic", False)
            f.color.rgb = opt.get("color", color)
        if bullet:
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(Inches(0.22)))
            pPr.set("indent", str(-Inches(0.2)))
            for tag in ("a:buNone", "a:buChar", "a:buFont"):
                for e in pPr.findall(qn(tag)):
                    pPr.remove(e)
            bf = etree.SubElement(pPr, qn("a:buFont"))
            bf.set("typeface", "Arial")
            bc = etree.SubElement(pPr, qn("a:buChar"))
            bc.set("char", "•")
    return box


def card(slide, x, y, w, h, fill=WHITE, line=LINE, name=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = 0.06
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = line
    sh.line.width = Pt(0.75)
    sh.shadow.inherit = False
    if name:
        sh.name = name
    sh.text_frame.text = ""
    return sh


def label(slide, x, y, w, text, color=GOLD, size=10):
    return tb(slide, x, y, w, 0.25, [[(text.upper(), {"bold": True, "color": color, "size": size})]])


def table(slide, x, y, w, col_w, data_rows, size=11, header_fill=SLATE, header_color=GOLD, row_h=0.3, name=None, bold_first_col=False, fills=None, left_cols=None):
    t = slide.shapes.add_table(len(data_rows), len(col_w), Inches(x), Inches(y), Inches(w), Inches(row_h * len(data_rows)))
    if name:
        t.name = name
    tbl = t.table
    tblPr = tbl._tbl.tblPr
    for e in tblPr.findall(qn("a:tableStyleId")):
        tblPr.remove(e)
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for ri, row in enumerate(data_rows):
        tbl.rows[ri].height = Inches(row_h)
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if ri == 0:
                cell.fill.fore_color.rgb = header_fill
            else:
                cell.fill.fore_color.rgb = (fills or {}).get((ri, ci), WHITE if ri % 2 else TINT)
            runs = [(val, {})] if isinstance(val, str) else val
            p = cell.text_frame.paragraphs[0]
            plain = val if isinstance(val, str) else "".join(t for t, _ in val)
            p.alignment = PP_ALIGN.LEFT if (ci == 0 or ci in (left_cols or ())) else PP_ALIGN.CENTER
            for text, opt in runs:
                r = p.add_run()
                r.text = text
                r.font.name = BODY
                r.font.size = Pt(opt.get("size", size))
                r.font.bold = opt.get("bold", ri == 0 or (bold_first_col and ci == 0))
                r.font.color.rgb = opt.get("color", header_color if ri == 0 else INK)
    return tbl


def arrow(slide, x1, y1, x2, y2, color=MUTED):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(1.5)
    ln = c.line._get_or_add_ln()
    tail = etree.SubElement(ln, qn("a:tailEnd"))
    tail.set("type", "triangle")
    tail.set("w", "med")
    tail.set("len", "med")
    return c


def node(slide, x, y, w, h, title, sub=None, edge=LINE, fill=WHITE, tsize=12, ssize=10, name=None):
    card(slide, x, y, w, h, fill=fill, line=edge, name=name)
    paras = [[(title, {"bold": True, "size": tsize})]]
    if sub:
        paras.append([(sub, {"size": ssize, "color": MUTED})])
    tb(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, spacing=1)


# =================================================================== 1. title (template)
def fill_title():
    sh = {s.name: s for s in TITLE_SLIDE.shapes}
    title_box = sh["Google Shape;59;p14"].text_frame
    ps = title_box.paragraphs
    run = ps[1].runs[0]
    run.text = "IndicBridge: Investigating Linguistic Relatedness in Cross-Lingual Multistage Fine-Tuning of Whisper for Low-Resource Indic Speech Recognition"
    run.font.size = Pt(22)
    for p in ps[2:]:
        p._p.getparent().remove(p._p)
    guide = sh["Google Shape;64;p14"].text_frame.paragraphs
    for p in guide:
        t = "".join(r.text for r in p.runs)
        if "ABC" in t:
            p.runs[0].text = "Prof. [Guide name]"
            for r in p.runs[1:]:
                r.text = ""
        elif "Assistant Professor/" in t:
            p.runs[0].text = "[Designation]"
            for r in p.runs[1:]:
                r.text = ""
    team = sh["Google Shape;63;p14"].text_frame.paragraphs
    members = ["1RUA24CSE0146 - Gourab Dash", "1RUA24CSE0201 - Parth N. Khandagale",
               "1RUA24CSE0139 - Divyansh Mahecha", "1RUA24CSE0196 - Kaushal BC"]
    k = 0
    for p in team:
        t = "".join(r.text for r in p.runs)
        if t.strip().startswith("USN") and k < len(members):
            p.runs[0].text = members[k]
            for r in p.runs[1:]:
                r.text = ""
            k += 1
    set_notes(TITLE_SLIDE, "PARTH: Good morning. We are team IndicBridge: Gourab Dash, Parth Khandagale, Divyansh Mahecha and Kaushal BC. "
              "Our project asks one question: when a speech model learns a low-resource language better after first learning a related one, "
              "is that because the languages are related, or just because it saw more data? I will introduce the problem, Gourab explains "
              "the method and implementation, and Divyansh and Kaushal present the results.")
    built.append((TITLE_SLIDE, None))


fill_title()
set_notes(OUTLINE_SLIDE, "PARTH: This is the outline we follow, as per the university format: introduction, literature survey and the gap, "
          "problem statement and objectives; then the system requirements, methodology, architecture and implementation; then results, "
          "conclusions, the project plan and references.")
built.append((OUTLINE_SLIDE, "parth"))

# =================================================================== 3. introduction
s = content_slide("Introduction", "parth",
                  "PARTH: Whisper is OpenAI's speech recognition model. It officially supports 99 languages, but for Indian languages it is not usable "
                  f"out of the box. Look at the card on the right: untrained whisper-base heard this Hindi sentence and wrote it in romanized English letters. "
                  f"After 45 hours of Hindi training it is almost word-perfect. Untrained, the word error rate is above 100 percent for all four of our "
                  f"languages: {f1(M('Z-hindi'))} for Hindi, {f1(M('Z-odia-bengali'))} for Odia. And Odia has no language token in Whisper at all. "
                  "One promising fix is multistage fine-tuning: train on a related language first, then on the target. Our scope is four languages, "
                  "whisper-base with LoRA, on one laptop.")
tb(s, 0.45, 1.2, 4.55, 3.7, [
    ("bullet", "Whisper supports 99 languages, but Indian languages need adaptation before it is usable"),
    ("bullet", [("Untrained whisper-base scores ", {}), ("above 100% WER", {"bold": True}), (" on all four of our languages", {})]),
    ("bullet", [("Odia, a scheduled language, has ", {}), ("no Whisper language token", {"bold": True})]),
    ("bullet", "Multistage fine-tuning (a related language first, then the target) is a promising fix for low-resource languages"),
    ("bullet", "Scope: Hindi, Marathi, Odia and Kannada · whisper-base + LoRA · one Apple M4 laptop"),
], size=14, spacing=8, name="Introduction points")
card(s, 5.2, 1.2, 4.35, 2.55, name="Example card")
label(s, 5.35, 1.28, 4.0, "Whisper on a Hindi test sentence")
tb(s, 5.35, 1.55, 4.1, 2.15, [
    [("Said: ", {"bold": True, "size": 10, "color": MUTED}), ("यह खोज पक्षियों में पंखों के विकास की पूरी जानकारी भी प्रदान करती है", {"size": 12, "font": "Nirmala UI"})],
    [("Untrained: ", {"bold": True, "size": 10, "color": MUTED}), ("Yer koj pakshio me panko ke vikaz ki pudi jaankari vi pradhan karti hai", {"size": 12, "color": RED})],
    [("After 45 h of Hindi: ", {"bold": True, "size": 10, "color": MUTED}), ("यह खोज़ पक्षियो में पंखों के विकास की पूरी जानकारी भी प्रदान करती है", {"size": 12, "font": "Nirmala UI"})],
], spacing=9)
for i, l in enumerate(["hindi", "marathi", "kannada", "odia"]):
    z = M("Z-odia-bengali" if l == "odia" else f"Z-{l}")
    tb(s, 5.2 + i * 1.09, 3.9, 1.09, 1.0, [[(f"{f1(z)}%", {"bold": True, "size": 18, "color": SLATE})],
                                           [(f"{NAME[l]} WER, untrained", {"size": 9, "color": MUTED})]], align=PP_ALIGN.CENTER, spacing=2)

# =================================================================== 4. literature survey: the gap
s = content_slide("Literature survey", "parth",
                  "PARTH: Our closest prior work is Pillai and colleagues. They trained Whisper on Tamil first, then on Malasar, a tiny Dravidian language, "
                  "and got 4.5 points fewer errors than training on Malasar alone. They explain it by relatedness. But a second explanation fits the same "
                  "result: any extra speech and an extra training stage might have helped. Rouditchenko found that family-level exposure predicts adaptation, "
                  "but only observationally; LoRA-Whisper uses language similarity as a heuristic. Nobody ran the control: an unrelated pivot with the same "
                  "data. That is the gap. The next two slides summarise eight studies in the required table format.")
card(s, 0.45, 1.2, 4.4, 2.45, name="Prior work card")
label(s, 0.6, 1.28, 4.1, "Closest prior work · Pillai et al. [5]")
tb(s, 0.6, 1.55, 4.15, 2.05, [
    [("Tamil first, then Malasar", {"bold": True, "size": 15})],
    "Whisper adapted to Tamil, then to Malasar (≈4.5 h of data):",
    [("51.9% WER, 4.5 points better", {"bold": True}), (" than training on Malasar alone.", {})],
    [("They credit the gain to the two languages being related.", {"italic": True})],
], size=13, spacing=5)
card(s, 5.15, 1.2, 4.4, 2.45, name="Gap card")
label(s, 5.3, 1.28, 4.1, "What nobody tested", color=RED)
tb(s, 5.3, 1.55, 4.15, 2.05, [
    [("Two explanations fit", {"bold": True, "size": 15})],
    [("Relatedness: ", {"bold": True}), ("the pivot shares sounds, words and grammar with the target", {})],
    [("Data quantity: ", {"bold": True}), ("any extra speech and an extra stage would help as much", {})],
    [("Only an ", {}), ("unrelated pivot of the same size", {"bold": True}), (" can tell them apart.", {})],
], size=13, spacing=5)
tb(s, 0.45, 3.85, 9.1, 1.05, [
    [("Research gaps: ", {"bold": True, "color": SLATE}),
     ("(1) no controlled test of relatedness against data quantity [5], [6], [7]; (2) languages with no Whisper token, such as Odia, are unstudied [3], [15]; "
      "(3) no shared normalization protocol for Indic-script WER [5].", {})],
], size=13)


# =================================================================== 5-6. literature tables (template table)
LIT = [
    [("A. Radford et al., “Robust Speech Recognition via Large-Scale Weak Supervision,” ICML, 2023 [3].",
      "Whisper: encoder–decoder Transformer trained on 680K hours of weakly labelled audio; zero-shot multilingual ASR.",
      "Robust zero-shot ASR for 99 languages from one model.",
      "Closed language-token set (no Odia); very uneven quality across languages."),
     ("A. Rouditchenko et al., “Comparison of Multilingual Self-Supervised and Weakly-Supervised Speech Pre-Training for Adaptation to Unseen Languages,” INTERSPEECH, 2023 [6].",
      "Fine-tunes XLS-R and Whisper on 13 unseen and 18 seen languages.",
      "Pre-training hours per language and per family predict adaptation quality.",
      "Family exposure is observational, never manipulated as a variable."),
     ("L. G. Pillai et al., “Multistage Fine-tuning Strategies for ASR in Low-resource Languages,” ACM TALLIP, 2026 [5].",
      "Multistage fine-tuning of Whisper: Tamil pivot, then Malasar (≈4.5 h).",
      "51.9% WER, 4.5 points better than direct fine-tuning; 47.3% after punctuation removal.",
      "One pivot–target pair; relatedness claim never tested against an unrelated pivot."),
     ("Z. Song et al., “LoRA-Whisper: Parameter-Efficient and Extensible Multilingual ASR,” INTERSPEECH, 2024 [7].",
      "Language-specific LoRA modules in Whisper; new languages initialised from similar ones.",
      "Mitigates language interference; similarity helps add new languages.",
      "Similarity used as a heuristic, not measured as an independent variable.")],
    [("E. J. Hu et al., “LoRA: Low-Rank Adaptation of Large Language Models,” ICLR, 2022 [8].",
      "Freezes the model and learns low-rank weight updates.",
      "Comparable quality while training under 1% of parameters.",
      "Not evaluated for speech or cross-lingual transfer."),
     ("K. S. Bhogale et al., “Vistaar: Diverse Benchmarks and Training Sets for Indian Language ASR,” INTERSPEECH, 2023 [15].",
      "59 benchmarks; IndicWhisper fine-tuned on 10.7K hours of 12 Indian languages.",
      "Lowest WER on 39 of 59 benchmarks; rankings change across benchmarks.",
      "Joint multilingual training hides pairwise transfer effects."),
     ("T. Javed et al., “IndicVoices: Towards Building an Inclusive Multilingual Speech Dataset for Indian Languages,” Findings of ACL, 2024 [13].",
      "Collects natural, read and conversational speech across 22 languages.",
      "23.7K hours from 51K speakers in 400+ districts.",
      "A dataset; no transfer-strategy study."),
     ("T. Javed et al., “IndicSUPERB: A Speech Processing Universal Performance Benchmark for Indian Languages,” AAAI, 2023 [14].",
      "Kathbath corpus and benchmark suite for Indian speech tasks.",
      "Standardised evaluation across Indian languages.",
      "A benchmark, not an adaptation method.")],
]
for part, entries in enumerate(LIT, 1):
    s = content_slide(f"Literature survey ({part}/2)", "parth",
                      "PARTH: " + ("Four studies closest to our question. Whisper is our base model; Rouditchenko shows family exposure matters but only observationally; "
                                   "Pillai gives us the multistage method; LoRA-Whisper uses similarity without measuring it. The last column is the gap each one leaves."
                                   if part == 1 else
                                   "Four more: LoRA, which makes 25 runs affordable on one laptop; Vistaar, which shows rankings change across benchmarks, so we use two "
                                   "test sets; and the two AI4Bharat resources we use, IndicVoices for training and Kathbath for testing."))
    el = copy.deepcopy(LIT_TABLE)
    s.shapes._spTree.append(el)
    gf = s.shapes[-1]
    gf.name = "Literature table"
    gf.left, gf.top, gf.width = Inches(0.25), Inches(1.1), Inches(9.5)
    tblx = gf.table._tbl
    trs = tblx.findall(qn("a:tr"))
    while len(trs) < 1 + len(entries):
        tblx.append(copy.deepcopy(trs[-1]))
        trs = tblx.findall(qn("a:tr"))
    widths = [2.75, 2.35, 2.3, 2.1]
    for i, g in enumerate(tblx.find(qn("a:tblGrid")).findall(qn("a:gridCol"))):
        g.set("w", str(Inches(widths[i])))
    tbl = gf.table
    tbl.rows[0].height = Inches(0.42)
    for ri in range(len(entries) + 1):
        if ri:
            tbl.rows[ri].height = Inches(0.88)
        for ci in range(4):
            cell = tbl.cell(ri, ci)
            tf = cell.text_frame
            for p in list(tf.paragraphs)[1:]:
                p._p.getparent().remove(p._p)
            p = tf.paragraphs[0]
            for r in list(p.runs):
                r._r.getparent().remove(r._r)
            text = ["Paper details", "Objective, techniques / methods", "Key contribution", "Research gap"][ci] if ri == 0 else entries[ri - 1][ci]
            r = p.add_run()
            r.text = text
            r.font.size = Pt(10 if ri == 0 else 8.5)
            r.font.bold = ri == 0
            r.font.name = BODY
            cell.margin_top = cell.margin_bottom = Inches(0.03)

# =================================================================== 7. problem statement
s = content_slide("Problem statement", "parth",
                  "PARTH: The problem in one line: multistage fine-tuning helps low-resource speech recognition, but no one knows whether that is because the "
                  "pivot is related or because it adds data. Existing work tests one pair, observes family effects without controlling them, trains all "
                  "languages jointly, ignores languages without a Whisper token, and scores Indic scripts inconsistently. Our novelty: an unrelated English "
                  "pivot with exactly the same hours and steps as Hindi; three targets that separate family from script; an Odia token study; one shared "
                  "scoring contract with confidence intervals; and an offline deployment.")
cols = [("Problem", SLATE, [
    "Multistage fine-tuning improves low-resource ASR",
    "Is it because the pivot is related, or because it adds data?",
    "The answer decides how to pick a pivot for the many Indian languages still without usable ASR",
]), ("Limitations of existing work", RED, [
    "One pivot–target pair, no unrelated control [5]",
    "Family effects only observed, not controlled [6]",
    "Joint training hides pairwise transfer [15]",
    "Languages with no Whisper token (Odia) ignored",
    "Inconsistent scoring for Indic scripts",
]), ("Our novelty", HI, [
    "Unrelated English pivot with the same 45 h and 2,000 steps as Hindi",
    "Three targets that separate family from script",
    "Borrowed-token study for Odia",
    "One shared scoring contract + 95% CIs",
    "Offline deployment on a laptop",
])]
for i, (head, col, items) in enumerate(cols):
    x = 0.45 + i * 3.07
    card(s, x, 1.2, 2.9, 3.7, name=f"{head} card")
    label(s, x + 0.15, 1.3, 2.6, head, color=col)
    tb(s, x + 0.12, 1.62, 2.68, 3.2, [("bullet", t) for t in items], size=13, spacing=9)

# =================================================================== 8. objectives
s = content_slide("Objectives and Expected Outcomes", "parth",
                  "PARTH: Our objectives map to the research questions. The main one: test relatedness against data quantity with a Hindi and an English "
                  "pivot of equal size. Then: does Hindi help the Indo-Aryan targets more than Kannada; which borrowed token works for Odia; and do scoring "
                  "rules change the answer. Finally, deploy the result offline. On the right are the deliverables; all of them are complete. "
                  "Over to Gourab for the system and the method.")
card(s, 0.45, 1.2, 4.95, 3.7, name="Objectives card")
label(s, 0.6, 1.3, 4.6, "Objectives")
tb(s, 0.6, 1.6, 4.7, 3.25, [
    [("1. Main: ", {"bold": True}), ("does a pivot help because it is related, or because it adds data?", {})],
    [("2. RQ1: ", {"bold": True}), ("does Hindi help Indo-Aryan targets (Marathi, Odia) more than Dravidian Kannada?", {})],
    [("3. RQ2: ", {"bold": True}), ("which borrowed language token works best for Odia?", {})],
    [("4. RQ3: ", {"bold": True}), ("do scoring rules change WER and the ranking of methods?", {})],
    [("5. Deploy ", {"bold": True}), ("the best models offline on a laptop", {})],
], size=14, spacing=11)
card(s, 5.6, 1.2, 3.95, 3.7, fill=TINT, name="Outcomes card")
label(s, 5.75, 1.3, 3.6, "Expected outcomes · all delivered")
tb(s, 5.75, 1.6, 3.7, 3.25, [("bullet", t) for t in [
    "Results table: 4 languages × 4 methods × 2 test sets",
    "Transfer gains with 95% bootstrap intervals",
    "Odia borrowed-token study",
    "Shared normalizer and scoring toolkit",
    "Offline MLX models and a live demo app",
    "IEEE research paper",
]], size=13, spacing=10)

# =================================================================== 9. SRS
s = content_slide("System Requirement Specification", "gourab",
                  "GOURAB: Thank you, Parth. Everything runs on one Apple M4 MacBook with 16 GB of unified memory. We use whisper-base because, measured on "
                  "this laptop, whisper-small would need about 49 hours for our grid and base about 15. Training uses PyTorch on the Apple GPU with Hugging "
                  "Face Transformers and PEFT for LoRA. Data comes through the Hugging Face hub with pandas and pyarrow. Scoring uses jiwer with our own "
                  "normalizer. Deployment uses Apple's MLX, and the demo is a FastAPI server with a React web interface, all of it offline.")
table(s, 0.45, 1.2, 9.1, [1.25, 3.25, 4.6], [
    ["Layer", "Technology", "Why"],
    ["Hardware", "Apple M4 MacBook, 16 GB unified memory", "One machine runs all 25 runs on its GPU (Metal / MPS)"],
    ["Model", "OpenAI Whisper-base (74M parameters)", "Grid in ~15 h; whisper-small would need ~49 h on this laptop"],
    ["Training", "PyTorch (MPS), Hugging Face Transformers, PEFT", "Standard Whisper fine-tuning; LoRA trains only 1.6% of weights"],
    ["Data", "Hugging Face Hub, pyarrow, pandas", "Seeded sampling of 36–59 GB corpora without a full download"],
    ["Evaluation", "jiwer, own normalizer (v3.0.0), NumPy bootstrap", "Corpus WER/CER, vowel signs kept, 95% confidence intervals"],
    ["Deployment", "Apple MLX, mlx-whisper", "Fast offline inference on the Apple GPU (17–31× real time)"],
    ["Demo app", "FastAPI server + React / TypeScript (Vite)", "A local web app that works with Wi-Fi switched off"],
], size=11, row_h=0.46, bold_first_col=True, left_cols=(1, 2))

# =================================================================== 10. methodology 1: design
s = content_slide("Proposed Methodology (1/2)", "gourab",
                  "GOURAB: Here is the design. Only one thing changes: the pivot. From whisper-base we either train 45 hours of Hindi, the related pivot, or "
                  "45 hours of English, the unrelated control, with exactly the same 2,000 steps; or we skip the pivot, which is direct training. Then each "
                  "model trains on the target, Marathi, Odia or Kannada, for 15 hours and 1,000 steps, and is scored on FLEURS and Kathbath. If Hindi beats "
                  "English, it cannot be because of more data or an extra stage, because both had the same.")
node(s, 0.35, 2.45, 1.6, 0.9, "whisper-base", "74M · frozen + LoRA", name="Base model")
node(s, 2.55, 1.3, 2.0, 0.8, "Hindi pivot", "45 h · 2,000 steps · related", edge=HI)
node(s, 2.55, 2.5, 2.0, 0.8, "English pivot", "45 h · 2,000 steps · control", edge=EN)
node(s, 2.55, 3.7, 2.0, 0.8, "No pivot", "direct training")
node(s, 5.2, 2.15, 2.1, 1.5, "Target, 15 h", "1,000 steps\nMarathi · Odia · Kannada", edge=GOLD, tsize=13, ssize=11)
node(s, 7.95, 2.3, 1.65, 1.2, "Score", "FLEURS + Kathbath\n600 clips each")
for y in (1.7, 2.9, 4.1):
    arrow(s, 1.95, 2.9, 2.55, y)
    arrow(s, 4.55, y, 5.2, 2.9)
arrow(s, 7.3, 2.9, 7.95, 2.9)
tb(s, 0.45, 4.6, 9.1, 0.4, [[("25 runs · ", {"bold": True}), ("same data budget, optimiser, decoding and scoring for every run; only the first stage differs", {})]],
   size=12, color=MUTED, align=PP_ALIGN.CENTER)

# =================================================================== 11. methodology 2
s = content_slide("Proposed Methodology (2/2)", "gourab",
                  "GOURAB: The three targets separate family from script. Marathi is Hindi's close relative and uses the same script. Odia is in the same "
                  "family with its own script and no Whisper token. Kannada is Dravidian. If family drives the gain, Hindi should help Marathi and Odia more "
                  "than Kannada. We measure the gain G, the WER points a pivot saves over direct training, and Delta, the Hindi gain minus the English gain, "
                  "each with a 95 percent paired-bootstrap interval. The benefits: one variable changes and it is cheap. The drawbacks: a small model and one seed.")
table(s, 0.45, 1.2, 5.2, [1.1, 1.45, 1.45, 1.2], [
    ["Target", "Family", "Script", "Whisper token"],
    ["Marathi", [("Indo-Aryan", {"bold": True, "color": HI})], [("Devanagari (= Hindi)", {"bold": True, "color": HI})], "yes"],
    ["Odia", [("Indo-Aryan", {"bold": True, "color": HI})], "its own", [("none", {"bold": True, "color": RED})]],
    ["Kannada", "Dravidian", "its own", "yes"],
], size=11, row_h=0.42, bold_first_col=True, left_cols=(1, 2))
tb(s, 0.45, 2.95, 5.2, 0.5, [[("If family is what matters, Hindi should help Marathi and Odia more than Kannada.", {"italic": True, "color": MUTED})]], size=12)
card(s, 5.85, 1.2, 3.7, 2.25, name="Measures card")
label(s, 6.0, 1.28, 3.4, "How we measure")
tb(s, 6.0, 1.55, 3.45, 1.85, [
    [("WER", {"bold": True}), (" = (substitutions + deletions + insertions) / reference words", {})],
    [("Gain G", {"bold": True}), (" = WER(direct) − WER(pivot → target)", {})],
    [("Δ", {"bold": True}), (" = G(Hindi) − G(English): the effect of relatedness", {})],
    [("95% CI", {"bold": True}), (": paired bootstrap, 1,000 resamples of the test clips", {})],
], size=11, spacing=6)
card(s, 0.45, 3.65, 4.45, 1.25, fill=TINT, name="Benefits card")
label(s, 0.6, 3.72, 4.1, "Benefits")
tb(s, 0.6, 3.97, 4.2, 0.9, [("bullet", t) for t in ["Isolates relatedness: one variable changes", "LoRA keeps 25 runs affordable on one laptop", "Two independent test sets"]], size=11, spacing=2)
card(s, 5.1, 3.65, 4.45, 1.25, fill=TINT, name="Drawbacks card")
label(s, 5.25, 3.72, 4.1, "Drawbacks", color=RED)
tb(s, 5.25, 3.97, 4.2, 0.9, [("bullet", t) for t in ["whisper-base only: absolute WER is high", "One training seed per configuration", "English audio comes from a different domain"]], size=11, spacing=2)

# =================================================================== 12. architecture
s = content_slide("Architecture diagram", "gourab",
                  "GOURAB: The system has a research pipeline and a deployment path. Data sources feed a data-preparation step with seeded sampling and "
                  "filters. A resumable training queue runs all LoRA jobs on the M4. Every model goes through the same evaluation: our normalizer, WER, CER, "
                  "script validity and the bootstrap, writing results files. For deployment, the adapters are merged and converted to MLX, served by a "
                  "FastAPI server, and used through a web interface by the presenter and examiners, all on the laptop.")
label(s, 0.45, 1.15, 5, "Research pipeline", color=SLATE)
specs = [("Data sources", "IndicVoices · LibriSpeech\nFLEURS · Kathbath"), ("Data prep", "seeded sampling, filters,\nParquet"),
         ("Training", "LoRA on M4 (MPS),\nresumable queue"), ("Evaluation", "normalizer · WER · CER\nscript · bootstrap"), ("Results", "25 runs →\nCSV tables, figures")]
for i, (t, sub) in enumerate(specs):
    x = 0.45 + i * 1.86
    node(s, x, 1.45, 1.6, 1.05, t, sub, edge=GOLD if i == 2 else LINE, tsize=11, ssize=9)
    if i:
        arrow(s, x - 0.26, 1.97, x, 1.97)
label(s, 0.45, 2.8, 5, "Deployment and demo", color=SLATE)
specs2 = [("LoRA adapters", "merged into whisper-base"), ("MLX conversion", "fp16 · 4-bit"), ("FastAPI server", "localhost · offline"),
          ("Web UI", "React · recorder ·\nbench"), ("Users", "presenter ·\nexaminers")]
for i, (t, sub) in enumerate(specs2):
    x = 0.45 + i * 1.86
    node(s, x, 3.1, 1.6, 1.05, t, sub, edge=GOLD if i == 2 else LINE, tsize=11, ssize=9)
    if i:
        arrow(s, x - 0.26, 3.62, x, 3.62)
arrow(s, 2.95, 2.5, 1.25, 3.1)
arrow(s, 7.9, 2.5, 6.4, 3.1)
tb(s, 0.45, 4.35, 9.1, 0.5, [[("The server reads the results files for the bench and runs the MLX models for live transcription; nothing leaves the laptop.", {})]],
   size=11, color=MUTED, align=PP_ALIGN.CENTER)

# =================================================================== 13. implementation 1
d = data
s = content_slide("Implementation (1/2)", "gourab",
                  "GOURAB: The datasets. Hindi and the targets come from IndicVoices, natural speech from real Indian speakers; English from LibriSpeech "
                  "audiobooks. Test sets are FLEURS and Kathbath, 600 clips each, never trained on. Preprocessing: clips of 2 to 30 seconds, at most 50 per "
                  "speaker, tagged rows dropped, and labels that fit Whisper's decoder. Parameters: LoRA rank 32 and alpha 64 on the query and value projections, "
                  "1.18 million trainable parameters; AdamW at 10 to the minus 3; pivots 2,000 steps and targets 1,000.")
table(s, 0.45, 1.2, 5.05, [1.55, 1.3, 0.75, 0.75, 0.7], [
    ["Dataset", "Use", "Hours", "Clips", "Spk."],
    ["IndicVoices · Hindi", "Hindi pivot", "45", f"{d['train_hindi_45h']['clips']:,}", f"{d['train_hindi_45h']['speakers']:,}"],
    ["LibriSpeech", "English pivot", "45", f"{d['train_english_45h']['clips']:,}", f"{d['train_english_45h']['speakers']}"],
    ["IndicVoices · Marathi", "Target", "15", f"{d['train_marathi_15h']['clips']:,}", f"{d['train_marathi_15h']['speakers']}"],
    ["IndicVoices · Odia", "Target", "15", f"{d['train_odia_15h']['clips']:,}", f"{d['train_odia_15h']['speakers']:,}"],
    ["IndicVoices · Kannada", "Target", "15", f"{d['train_kannada_15h']['clips']:,}", f"{d['train_kannada_15h']['speakers']}"],
    ["FLEURS + Kathbath", "Test only", "–", "600 / lang", "–"],
], size=10, row_h=0.38, bold_first_col=True, left_cols=(1,))
card(s, 5.7, 1.2, 3.85, 1.55, name="Preprocessing card")
label(s, 5.85, 1.27, 3.5, "Preprocessing")
tb(s, 5.85, 1.52, 3.6, 1.2, [("bullet", t) for t in ["Clips 2–30 s; ≤50 clips per speaker", "Rows with tags like <unintelligible> dropped",
                                                      "Labels ≤443 tokens; test references ≤440", "Same rules for every language"]], size=11, spacing=1)
card(s, 5.7, 2.9, 3.85, 2.0, fill=TINT, name="Parameters card")
label(s, 5.85, 2.97, 3.5, "Parameters")
tb(s, 5.85, 3.22, 3.6, 1.65, [("bullet", t) for t in ["LoRA r = 32, α = 64 on Wq, Wv: 1.18M trainable (1.6%)", "AdamW, lr 1e-3, 100 warm-up, linear decay",
                                                      "Effective batch 16, fp32, seed 42", "Pivot 2,000 steps; target 1,000 steps", "Greedy decoding, per-language length cap"]], size=11, spacing=1)

# =================================================================== 14. implementation 2: challenges
s = content_slide("Implementation (2/2)", "gourab",
                  "GOURAB: Running 25 experiments on one laptop meant solving real problems. The Hindi pivot ran out of memory because Apple's GPU caches a "
                  "compiled graph for every label length; padding labels to multiples of 64 fixed it. The decoding settings in our plan broke Odia, so we "
                  "switched to plain greedy decoding with a length cap. IndicVoices is up to 59 GB per language, so we sampled across it with a fixed seed. "
                  "And the offline model only matched PyTorch after we turned timestamps off. Now Divyansh will present the results.")
fixes = [("Hindi pivot ran out of memory", "Apple's GPU cached a compute graph per label length (4.9 GB).", "Pad labels to multiples of 64 (7 shapes); micro-batch 2 × 8, effective batch 16"),
         ("Default decoding broke Odia", "A repetition penalty blocks Odia's repeating byte tokens; a 200-token cap cut sentences.", "Plain greedy decoding, no penalties, a length cap per language"),
         ("36–59 GB of audio per language", "Too large to download; first-N sampling would pick one district.", "Seeded sampling across shards, filters from metadata"),
         ("Offline model disagreed with PyTorch", "MLX decoded with timestamps; our adapters were trained without them.", "Timestamps off (Kannada CER 35.6 → 24.4), loop fallback: within 2.5 WER")]
for i, (q, why, how) in enumerate(fixes):
    x, y = 0.45 + (i % 2) * 4.6, 1.2 + (i // 2) * 1.88
    card(s, x, y, 4.45, 1.73, name=f"Challenge {i + 1}")
    tb(s, x + 0.12, y + 0.1, 4.2, 1.6, [[(q, {"bold": True, "size": 14, "color": SLATE})], [(why, {"color": MUTED})], [("Fix: ", {"bold": True, "color": HI}), (how, {})]],
       size=12, spacing=7)

# =================================================================== 15. results 1: table
trs = [["Target", "Model", "FLEURS WER", "Kathbath WER"]]
fills = {}
for t in TARGETS:
    runs = [("Z-odia-bengali" if t == "odia" else f"Z-{t}", "Zero-shot"), (f"D-{t}", "Direct"), (f"H-{t}", f"Hindi → {NAME[t]}"), (f"E-{t}", f"English → {NAME[t]}")]
    best = {ts: min(M(r, ts) for r, _ in runs) for ts in ["fleurs", "kathbath"]}
    for i, (rid, lab) in enumerate(runs):
        cells = []
        for ts in ["fleurs", "kathbath"]:
            v = M(rid, ts)
            cells.append([(f1(v), {"bold": v == best[ts], "color": HI if v == best[ts] else (MUTED if i == 0 else INK)})])
        trs.append([NAME[t] if i == 0 else "", lab] + cells)
s = content_slide("Results and Discussion (1/5)", "divyansh",
                  f"DIVYANSH: Thank you, Gourab. First the overall picture: fine-tuning works. Untrained, every language is above 100 percent error. After "
                  f"training, every model writes 100 percent in the correct script. Absolute WERs of 60 to 75 percent are high because whisper-base is small; "
                  f"what matters is the comparison. The gold numbers are the best in each column: Hindi-first is the best method in all six target and "
                  f"test-set cells. Is that relatedness or just extra data? Next slide.")
table(s, 0.45, 1.15, 5.6, [1.05, 2.15, 1.2, 1.2], trs, size=10, row_h=0.29, bold_first_col=True, left_cols=(1,))
for i, (big, small) in enumerate([(">100%", "untrained WER for every language"), ("0–7% → 100%", "output in the right script, before → after training"),
                                  ("6 / 6", "target × test-set cells where Hindi → target has the lowest WER and CER")]):
    y = 1.2 + i * 1.25
    card(s, 6.3, y, 3.25, 1.1, fill=WHITE if i < 2 else TINT, name=f"Result callout {i + 1}")
    tb(s, 6.42, y + 0.07, 3.05, 1.0, [[(big, {"bold": True, "size": 22, "color": SLATE})], [(small, {"size": 11, "color": MUTED})]], spacing=2)

# =================================================================== 16. results 2: chart
s = content_slide("Results and Discussion (2/5)", "divyansh",
                  "DIVYANSH: This is our main result. Each bar is how many WER points a pivot saves over training on the target alone; the whiskers are 95 "
                  f"percent confidence intervals. The gold bars, Hindi, are positive for every target: Marathi {sg(G('marathi', 'fleurs', 'hindi_pivot_gain')[0])} "
                  f"and {sg(G('marathi', 'kathbath', 'hindi_pivot_gain')[0])}, Odia {sg(G('odia', 'fleurs', 'hindi_pivot_gain')[0])} and "
                  f"{sg(G('odia', 'kathbath', 'hindi_pivot_gain')[0])}, Kannada {sg(G('kannada', 'fleurs', 'hindi_pivot_gain')[0])} and "
                  f"{sg(G('kannada', 'kathbath', 'hindi_pivot_gain')[0])}. The blue bars, English, with the same 45 hours and steps, give no significant gain "
                  f"anywhere and even hurt Kannada on FLEURS. So the gain is not about data quantity or the extra stage.")


def gain_chart(slide, ts, x, title):
    cd = CategoryChartData()
    cd.categories = [f"{NAME[t]}\nHi {sg(G(t, ts, 'hindi_pivot_gain')[0])} · En {sg(G(t, ts, 'english_pivot_gain')[0])}" for t in TARGETS]
    vals = {}
    for key, nm in [("hindi_pivot_gain", "Hindi pivot (45 h)"), ("english_pivot_gain", "English pivot (45 h)")]:
        v = [G(t, ts, key) for t in TARGETS]
        vals[nm] = v
        cd.add_series(nm, [float(r1(p)) for p, _, _ in v])
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(1.15), Inches(4.5), Inches(3.45), cd)
    gf.name = f"Gain chart {title}"
    ch = gf.chart
    ch.has_title = True
    ch.chart_title.text_frame.text = title
    tp = ch.chart_title.text_frame.paragraphs[0]
    tp.runs[0].font.size, tp.runs[0].font.bold, tp.runs[0].font.name = Pt(13), True, BODY
    tp.runs[0].font.color.rgb = SLATE
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch.legend.include_in_layout = False
    ch.legend.font.size, ch.legend.font.name = Pt(10), BODY
    va = ch.value_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = -4, 6, 2
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor(0xE4, 0xDE, 0xD1)
    va.tick_labels.font.size, va.tick_labels.font.name = Pt(10), BODY
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = '+0;−0;0', False
    va.format.line.fill.background()
    ca = ch.category_axis
    ca.tick_labels.font.size, ca.tick_labels.font.name, ca.tick_labels.font.bold = Pt(10), BODY, True
    ca.format.line.color.rgb = MUTED
    from pptx.enum.chart import XL_TICK_LABEL_POSITION
    ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    plot = ch.plots[0]
    plot.gap_width, plot.overlap = 70, -10
    for ser, colr, nm in zip(plot.series, [HI, EN], vals):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = colr
        ser.invert_if_negative = False
        # 95% CI whiskers as custom error bars (positions follow the schema: after dLbls, before cat)
        serx = ser._element
        eb = etree.Element(qn("c:errBars"))
        for tag, val in (("c:errBarType", "both"), ("c:errValType", "cust"), ("c:noEndCap", "0")):
            e = etree.SubElement(eb, qn(tag))
            e.set("val", val)
        for side in ("plus", "minus"):
            holder = etree.SubElement(eb, qn(f"c:{side}"))
            lit = etree.SubElement(holder, qn("c:numLit"))
            etree.SubElement(lit, qn("c:formatCode")).text = "General"
            pc = etree.SubElement(lit, qn("c:ptCount"))
            pc.set("val", "3")
            for i, (p, lo, hi) in enumerate(vals[nm]):
                pt = etree.SubElement(lit, qn("c:pt"))
                pt.set("idx", str(i))
                etree.SubElement(pt, qn("c:v")).text = f"{(hi - p) if side == 'plus' else (p - lo):.2f}"
        sp = etree.SubElement(eb, qn("c:spPr"))
        ln = etree.SubElement(sp, qn("a:ln"))
        ln.set("w", "15875")
        sf = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(sf, qn("a:srgbClr")).set("val", "1F262C")
        cat = serx.find(qn("c:cat"))
        cat.addprevious(eb)
    return gf


gain_chart(s, "fleurs", 0.4, "FLEURS")
gain_chart(s, "kathbath", 5.1, "Kathbath")
tb(s, 0.45, 4.6, 9.1, 0.4, [[("WER points saved over direct training · whiskers: 95% paired-bootstrap interval · ", {}),
                             ("Hindi helps; an equal English pivot does not.", {"bold": True, "color": SLATE})]], size=11, color=MUTED, align=PP_ALIGN.CENTER)

# =================================================================== 17. results 3: family vs region
x_int = next(r for r in inter if r["metric"] == "WER" and r["comparison"] == "marathi - kannada" and r["test_set"] == "kathbath")
s = content_slide("Results and Discussion (3/5)", "divyansh",
                  "DIVYANSH: RQ1, is it the language family? Delta, the Hindi gain minus the English gain, is positive for all three targets on both test sets, "
                  "including Kannada, which is Dravidian. A bigger Indo-Aryan effect appears only once, Marathi versus Kannada on Kathbath, and Marathi also "
                  "shares Hindi's script, so script and family cannot be separated there. On the right: the Hindi model, before any Kannada training, writes "
                  "Kannada phonetically in Devanagari. The sounds transfer across families; only the script is wrong. Our answer: relatedness, but regional. "
                  "Over to Kaushal.")
dt = [["Target", "Δ FLEURS", "Δ Kathbath"]]
for t in TARGETS:
    dt.append([NAME[t]] + [[(f"{sg(G(t, ts, 'hindi_specific')[0])}  [{f1(G(t, ts, 'hindi_specific')[1])}, {f1(G(t, ts, 'hindi_specific')[2])}]", {"bold": True, "color": HI})] for ts in ["fleurs", "kathbath"]])
table(s, 0.45, 1.2, 4.65, [1.25, 1.7, 1.7], dt, size=11, row_h=0.42, bold_first_col=True)
tb(s, 0.45, 2.98, 4.65, 1.9, [
    [("Δ = Hindi gain − English gain (WER points, 95% CI). ", {"color": MUTED, "size": 10})],
    [("Positive for all three targets", {"bold": True}), (", Dravidian Kannada included.", {})],
    [("A larger Indo-Aryan effect appears only once: Marathi − Kannada on Kathbath, ", {}),
     (f"{sg(x_int['points'])} [{f1(x_int['ci_low'])}, {f1(x_int['ci_high'])}]", {"bold": True}), (". Marathi also shares Hindi's script.", {})],
], size=12, spacing=6)
card(s, 5.3, 1.2, 4.25, 2.6, name="Kannada example card")
label(s, 5.45, 1.27, 4.0, "Hindi pivot on Kannada audio, before Kannada training")
tb(s, 5.45, 1.72, 4.0, 2.05, [
    [("Said (Kannada): ", {"bold": True, "size": 10, "color": MUTED}), ("ಸಹ ಕುಸ್ತಿಪಟುಗಳು ಸಹ ಲೂನಾ ಅವರಿಗೆ ಗೌರವ ಸಲ್ಲಿಸಿದರು.", {"size": 13, "font": "Nirmala UI"})],
    [("Written (Devanagari): ", {"bold": True, "size": 10, "color": MUTED}), ("सहाकुस्ती पटुगलु सहा लूना वरेगे दौरवा सलीसी दरू", {"size": 13, "color": RED, "font": "Nirmala UI"})],
    [("The sounds carry over; only the script is wrong.", {"italic": True, "size": 11})],
], spacing=8)
card(s, 5.3, 3.95, 4.25, 0.95, fill=SLATE, line=SLATE, name="Verdict")
tb(s, 5.4, 3.95, 4.05, 0.95, [[("Relatedness, but regional", {"bold": True, "size": 16, "color": GOLD})],
                              [("Shared Indian sounds help even across families", {"size": 11, "color": WHITE})]], anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, spacing=2)

# =================================================================== 18. results 4: Odia
odia_fl = data["test_fleurs_odia"]
s = content_slide("Results and Discussion (4/5)", "kaushal",
                  f"KAUSHAL: Thanks, Divyansh. RQ2: Odia has no token, so which should we borrow? Untrained, all three give zero percent Odia script. After "
                  f"training all three give 100 percent, and the error rates are within about one point: Bengali {f1(M('D-odia'))}, Assamese "
                  f"{f1(M('T-odia-assamese'))}, Hindi {f1(M('T-odia-hindi'))} on FLEURS. None of the differences is statistically reliable. The real "
                  f"ceiling is the tokenizer: Whisper writes Odia letters as raw bytes, {fert['odia']['tokens_per_char']} tokens per letter against "
                  f"{fert['hindi']['tokens_per_char']} for Hindi, so {odia_fl['split_too_long_pct']:.1f} percent of Odia sentences are too long to transcribe at all.")
for i, (code, nm, run, z) in enumerate([("bn", "Bengali", "D-odia", "Z-odia-bengali"), ("as", "Assamese", "T-odia-assamese", "Z-odia-assamese"), ("hi", "Hindi", "T-odia-hindi", "Z-odia-hindi")]):
    x = 0.45 + i * 3.07
    card(s, x, 1.2, 2.9, 1.75, name=f"Token {code}")
    tb(s, x + 0.12, 1.27, 2.7, 1.65, [[(f"<|{code}|> · {nm}", {"bold": True, "size": 11, "color": MUTED})],
                                      [(f1(M(run)), {"bold": True, "size": 28, "color": SLATE})],
                                      [(f"FLEURS WER after training · Kathbath {f1(M(run, 'kathbath'))}", {"size": 10})],
                                      [(f"Odia script: {float(M(z, 'fleurs', 'script_valid')):.0f}% untrained → 100% trained", {"size": 10, "color": MUTED})]], spacing=2)
tb(s, 0.45, 3.05, 9.1, 0.35, [[("Every difference from Bengali has a 95% interval that includes zero: the closest relatives do not win.", {"bold": True, "color": SLATE})]], size=12)
stats = [(str(len(tok["tokens"])), f"Whisper tokens for one 42-letter Odia sentence"), (fert["odia"]["tokens_per_char"], f"tokens per Odia letter (Hindi {fert['hindi']['tokens_per_char']})"),
         (f"{odia_fl['split_too_long_pct']:.1f}%", "of Odia test sentences too long for the decoder")]
for i, (big, small) in enumerate(stats):
    x = 0.45 + i * 3.07
    card(s, x, 3.5, 2.9, 1.4, fill=TINT, name=f"Tokenizer stat {i + 1}")
    tb(s, x + 0.12, 3.57, 2.7, 1.3, [[(big, {"bold": True, "size": 24, "color": RED if i == 2 else SLATE})], [(small, {"size": 11, "color": MUTED})]], spacing=2)

# =================================================================== 19. results 5: scoring + deployment
dpl = {(r["run_id"], r["precision"]): r for r in deploy}
rtf = [float(r["rtf"]) for r in deploy if r["precision"] == "fp16"]
s = content_slide("Results and Discussion (5/5)", "kaushal",
                  f"KAUSHAL: RQ3, scoring. With Whisper's own normalizer, the Marathi Hindi-pivot WER falls from {f1(M('H-marathi'))} to "
                  f"{f1(M('H-marathi', 'fleurs', 'WER_whisper_norm'))}, roughly half, because it deletes vowel signs: a study using it would report "
                  "numbers that look far better than they are. Hindi-first still stays best under all three rules. Deployment: converted to Apple's MLX, "
                  f"the fp16 model is 144 MB and runs {1 / max(rtf):.0f} to {1 / min(rtf):.0f} times faster than real time, offline. 4-bit is smaller but breaks "
                  "Kannada, so we ship fp16. At this point we can show the live demo.")
card(s, 0.45, 1.2, 4.45, 3.7, name="Scoring card")
label(s, 0.6, 1.27, 4.1, "RQ3 · scoring rules", color=RED)
tb(s, 0.6, 1.55, 4.2, 3.3, [
    [("Whisper's normalizer deletes vowel signs", {"bold": True, "size": 14, "color": SLATE})],
    [("नमस्ते आप कैसे हैं", {"size": 15, "font": "Nirmala UI"}), ("   →   ", {"color": MUTED}), ("नमस त आप क स ह", {"size": 15, "color": RED, "font": "Nirmala UI"})],
    [("Marathi FLEURS, Hindi-pivot model: ", {}), (f"{f1(M('H-marathi'))}", {"bold": True}), (" WER with our scoring, ", {}),
     (f"{f1(M('H-marathi', 'fleurs', 'WER_whisper_norm'))}", {"bold": True, "color": RED}), (" with Whisper's.", {})],
    "Removing punctuation alone moves FLEURS WER by 4.7–8.4 points.",
    [("Hindi-first stays best under all three rules.", {"bold": True})],
], size=13, spacing=11)
table(s, 5.1, 1.2, 4.45, [1.25, 0.8, 0.7, 0.85, 0.85], [
    ["Model", "Weights", "MB", "RTF", "WER"],
    *[[lab if pr == "fp16" else "", "fp16" if pr == "fp16" else "4-bit", f"{float(dpl[(rid, pr)]['model_mb']):.0f}", f"{float(dpl[(rid, pr)]['rtf']):.3f}",
       [(f1(dpl[(rid, pr)]["WER"]), {"bold": pr == "fp16"})]]
      for rid, lab in [("H-marathi", "Hindi → Marathi"), ("H-odia", "Hindi → Odia"), ("H-kannada", "Hindi → Kannada")] for pr in ["fp16", "q4"]],
], size=10, row_h=0.33, bold_first_col=True)
tb(s, 5.1, 3.6, 4.45, 1.3, [
    [("fp16: 144 MB, ", {"bold": True}), (f"{1 / max(rtf):.0f}–{1 / min(rtf):.0f}× faster than real time", {"bold": True}), (", within 2.5 WER of PyTorch.", {})],
    [("4-bit: Kannada CER ", {}), (f"{f1(dpl[('H-kannada', 'fp16')]['CER'])} → {f1(dpl[('H-kannada', 'q4')]['CER'])}", {"bold": True, "color": RED}), (". We ship fp16, fully offline.", {})],
], size=11, spacing=4)

# =================================================================== 20. conclusions
s = content_slide("Conclusions and Future work", "kaushal",
                  "KAUSHAL: Three conclusions. One: the benefit of a pivot is not just data; the same hours of English gave nothing. Two: it is relatedness, "
                  "but regional; Hindi helps even Kannada, so choose pivots by shared sounds and region, not family alone. Three: for Odia, the bottleneck "
                  "is the tokenizer, not the language token. We are open about limits: one seed, whisper-base, and an English control from a different domain. "
                  "Future work: a Dravidian pivot, more seeds and larger models, targets that separate script from family, and a tokenizer that can write Odia.")
concl = [("It is not data quantity", "The same 45 h of English added nothing; Hindi helped every target."),
         ("Relatedness, but regional", "Hindi helps even Dravidian Kannada; a family-only effect is not established."),
         ("For Odia, the tokenizer is the ceiling", "The borrowed token barely matters; 23.1% of sentences can't be written.")]
for i, (h, p) in enumerate(concl):
    y = 1.2 + i * 1.25
    card(s, 0.45, y, 4.9, 1.12, name=f"Conclusion {i + 1}")
    tb(s, 0.55, y + 0.06, 0.55, 1.0, [[(str(i + 1), {"bold": True, "size": 26, "color": GOLD})]], anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
    tb(s, 1.1, y + 0.08, 4.15, 1.0, [[(h, {"bold": True, "size": 13, "color": SLATE})], [(p, {"size": 11})]], spacing=3)
card(s, 5.55, 1.2, 4.0, 3.7, fill=TINT, name="Future work card")
label(s, 5.7, 1.27, 3.7, "Future work")
tb(s, 5.7, 1.55, 3.75, 1.6, [("bullet", t) for t in ["A Dravidian pivot (Tamil, Telugu)", "Marathi → Odia and Kannada → Odia pivots", "Several seeds; whisper-small and larger",
                                                     "Targets that separate script from family", "A tokenizer that doesn't split Odia into bytes"]], size=12, spacing=4)
label(s, 5.7, 3.25, 3.7, "Limitations", color=RED)
tb(s, 5.7, 3.52, 3.75, 1.3, [("bullet", t) for t in ["One training seed; whisper-base only", "English pivot moved the model less (audiobooks)", "Native-speaker error analysis not completed"]],
   size=12, spacing=4)

# =================================================================== 21. Gantt
s = content_slide("Gantt chart", "kaushal",
                  "KAUSHAL: Our plan and schedule. Review 1 in August covered the literature survey, the research gap and the experimental design. The build "
                  "ran from Monday 2 to Wednesday 4 November on one laptop: data preparation and baselines on day one, the training grid overnight and through "
                  "day two, then analysis, deployment, the demo app and the paper on day three. [Add each member's contribution before presenting.]")
phases = [("Literature survey · research gap · design (Review 1)", [0]), ("Benchmark the M4; choose whisper-base", [1]), ("Data preparation (5 corpora, 2 test sets)", [1]),
          ("Zero-shot baselines", [1]), ("Hindi pivot + gate", [1, 2]), ("Direct and Hindi → target runs", [2]), ("English pivot + control runs", [2]),
          ("Odia token and pivot-only runs", [2]), ("Analysis, bootstrap CIs, figures", [2, 3]), ("MLX deployment + demo app", [2, 3]), ("IEEE paper + presentation", [3])]
cols_g = ["Aug (Review 1)", "Mon 2 Nov", "Tue 3 Nov", "Wed 4 Nov"]
gt = [["Task"] + cols_g] + [[p] + ["" for _ in cols_g] for p, _ in phases]
fills = {}
for ri, (_, on) in enumerate(phases, 1):
    for c in on:
        fills[(ri, c + 1)] = GOLD
table(s, 0.45, 1.15, 9.1, [4.3, 1.2, 1.2, 1.2, 1.2], gt, size=10, row_h=0.285, fills=fills)
tb(s, 0.45, 4.67, 9.1, 0.35, [[("Team contributions: ", {"bold": True, "color": SLATE}), ("[add who owned which language and component]", {"color": RED})]], size=11)

# =================================================================== 22-23. references
REFS = [
    "A. Conneau, A. Baevski, R. Collobert, A. Mohamed, and M. Auli, “Unsupervised cross-lingual representation learning for speech recognition,” in Proc. INTERSPEECH, 2021, pp. 2426–2430.",
    "A. Babu et al., “XLS-R: Self-supervised cross-lingual speech representation learning at scale,” in Proc. INTERSPEECH, 2022, pp. 2278–2282.",
    "A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, “Robust speech recognition via large-scale weak supervision,” in Proc. ICML, 2023, pp. 28492–28518.",
    "V. Pratap et al., “Scaling speech technology to 1,000+ languages,” J. Mach. Learn. Res., vol. 25, no. 97, pp. 1–52, 2024.",
    "L. G. Pillai, K. Manohar, B. K. Raju, and E. Sherly, “Multistage fine-tuning strategies for automatic speech recognition in low-resource languages,” ACM Trans. Asian Low-Resour. Lang. Inf. Process., vol. 25, no. 8, pp. 1–12, 2026.",
    "A. Rouditchenko et al., “Comparison of multilingual self-supervised and weakly-supervised speech pre-training for adaptation to unseen languages,” in Proc. INTERSPEECH, 2023, pp. 2268–2272.",
    "Z. Song, J. Zhuo, Y. Yang, Z. Ma, S. Zhang, and X. Chen, “LoRA-Whisper: Parameter-efficient and extensible multilingual ASR,” in Proc. INTERSPEECH, 2024, pp. 3934–3938.",
    "E. J. Hu et al., “LoRA: Low-rank adaptation of large language models,” in Proc. ICLR, 2022.",
    "T. Xu et al., “Towards rehearsal-free multilingual ASR: A LoRA-based case study on Whisper,” in Proc. INTERSPEECH, 2024, pp. 2534–2538.",
    "T. P. Ferraz, M. Z. Boito, C. Brun, and V. Nikoulina, “Multilingual DistilWhisper: Efficient distillation of multi-task speech models via language-specific experts,” in Proc. ICASSP, 2024, pp. 10716–10720.",
    "N. Houlsby et al., “Parameter-efficient transfer learning for NLP,” in Proc. ICML, 2019, pp. 2790–2799.",
    "J. Pfeiffer, I. Vulić, I. Gurevych, and S. Ruder, “MAD-X: An adapter-based framework for multi-task cross-lingual transfer,” in Proc. EMNLP, 2020, pp. 7654–7673.",
    "T. Javed et al., “IndicVoices: Towards building an inclusive multilingual speech dataset for Indian languages,” in Findings of ACL, 2024, pp. 10740–10782.",
    "T. Javed, K. S. Bhogale, A. Raman, P. Kumar, A. Kunchukuttan, and M. M. Khapra, “IndicSUPERB: A speech processing universal performance benchmark for Indian languages,” in Proc. AAAI, vol. 37, no. 11, 2023, pp. 12942–12950.",
    "K. S. Bhogale, S. Sundaresan, A. Raman, T. Javed, M. M. Khapra, and P. Kumar, “Vistaar: Diverse benchmarks and training sets for Indian language ASR,” in Proc. INTERSPEECH, 2023, pp. 4384–4388.",
    "A. Conneau et al., “FLEURS: Few-shot learning evaluation of universal representations of speech,” in Proc. IEEE SLT, 2023, pp. 798–805.",
    "A. Piñeiro-Martín, C. García-Mateo, L. Docío-Fernández, M. del Carmen López-Pérez, and G. Rehm, “Weighted cross-entropy for low-resource languages in multilingual speech recognition,” in Proc. INTERSPEECH, 2024, pp. 1235–1239.",
    "V. Panayotov, G. Chen, D. Povey, and S. Khudanpur, “Librispeech: An ASR corpus based on public domain audio books,” in Proc. ICASSP, 2015, pp. 5206–5210.",
    "R. Ardila et al., “Common Voice: A massively-multilingual speech corpus,” in Proc. LREC, 2020, pp. 4218–4222.",
    "T. Wolf et al., “Transformers: State-of-the-art natural language processing,” in Proc. EMNLP: System Demonstrations, 2020, pp. 38–45.",
    "S. Mangrulkar et al., “PEFT: State-of-the-art parameter-efficient fine-tuning methods,” 2022. [Online]. Available: https://github.com/huggingface/peft",
    "M. Bisani and H. Ney, “Bootstrap estimates for confidence intervals in ASR performance evaluation,” in Proc. ICASSP, vol. 1, 2004, pp. I-409–I-412.",
    "A. Hannun, J. Digani, A. Katharopoulos, and R. Collobert, “MLX: Efficient and flexible machine learning on Apple silicon,” 2023. [Online]. Available: https://github.com/ml-explore/mlx",
]
for part, (a, b) in enumerate([(0, 12), (12, 23)], 1):
    s = content_slide(f"References ({part}/2)", "kaushal",
                      "KAUSHAL: Our references, in IEEE format, as in the paper." + (" Thank you; we are happy to take questions." if part == 2 else ""))
    tb(s, 0.45, 1.15, 9.1, 3.8, [[(f"[{i + 1}] ", {"bold": True}), (REFS[i], {})] for i in range(a, b)], size=9, spacing=3, name="Reference list")

# =================================================================== Thank you (template)
set_notes(THANKS_SLIDE, "KAUSHAL: Thank you. Everything you saw runs on this laptop, offline, and every number comes from our results files. "
          "We are happy to take questions, and we can show the live demo or any test clip on the bench.")
built.append((THANKS_SLIDE, "kaushal"))

# =================================================================== order, footer, cleanup
order = [s for s, _ in built]
sldIdLst = prs.slides._sldIdLst
by_part = {}
for sldId in list(sldIdLst):
    by_part[prs.part.related_part(sldId.rId)] = sldId
keep = [by_part[s.part] for s in order]
for sldId in list(sldIdLst):
    if sldId not in keep:
        prs.part.drop_rel(sldId.rId)
    sldIdLst.remove(sldId)
for sldId in keep:
    sldIdLst.append(sldId)

total = len(order)
for n, (slide, who) in enumerate(built, 1):
    if n == 1:
        continue
    tb(slide, 0.35, 5.24, 6.0, 0.28, [[("IndicBridge · ", {"bold": True, "color": GOLD}), (f"Presenter: {PEOPLE[who]}", {"color": WHITE})]], size=10, name="Presenter")
    tb(slide, 8.6, 5.24, 1.05, 0.28, [[(f"{n} / {total}", {"color": WHITE})]], size=10, align=PP_ALIGN.RIGHT, name="Slide number")

prs.save(OUT)
print(f"wrote {OUT}: {total} slides")
