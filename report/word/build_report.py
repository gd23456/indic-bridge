"""
build_report.py - the project report in RV University's report format (A4, Times New Roman 12,
1.5 spacing, margins 3.81 / 2.54 cm, chapter 16 bold, section 14 caps, subsection 12 caps, roman
page numbers for the front matter and arabic from Chapter 1, APA references).

    <python with python-docx> report/word/build_report.py OUT.docx [pages.json]

Chapter text is the team's own wording, taken from the revised IEEE paper (report/paper/revised_wording.tex) with
citations converted to APA author-date. Every table is generated from results/ and data/.
pages.json (from a first render) fills the page numbers in the contents and lists.
"""
import csv
import json
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.shared import Cm, Pt, RGBColor
from PIL import ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.join(ROOT, "report", "word")
OUT = sys.argv[1]
PAGES = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else {}
BREAKS = set(PAGES.get("_breaks", []))   # tables whose caption was stranded at a page foot (found by page_map.py)

TNR = "Times New Roman"
BLACK, RED, GREY = RGBColor(0, 0, 0), RGBColor(0xC0, 0x00, 0x00), RGBColor(0x40, 0x40, 0x40)
TEXT_W = 21.0 - 3.81 - 2.54  # cm
TITLE = ("IndicBridge: Investigating Linguistic Relatedness in Cross-Lingual Multistage Fine-Tuning "
         "of Whisper for Low-Resource Indic Speech Recognition")
DEGREE = "Bachelor of Technology (Hons.)"
TEAM = [("Gourab Dash", "1RUA24CSE0146"), ("Parth Nandkumar Khandagale", "1RUA24CSE0201"),
        ("Divyansh Mahecha", "1RUA24CSE0139"), ("Kaushal BC", "1RUA24CSE0196")]
GUIDE, GUIDE_DESIG, DEAN = "Dr. Jeethu Devasia", "[Designation]", "Dr. G Shobha"


# ======================================================================= data
def rows(path):
    with open(os.path.join(ROOT, path), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


master = rows("results/results_master.csv")
gains = rows("results/tables/gains.csv")
inter = rows("results/tables/interaction.csv")
fert = {r["language"]: r for r in rows("results/tables/fertility.csv")}
deploy = rows("results/tables/deployment.csv")
pivots = {r["pivot"]: r for r in rows("results/tables/pivots.csv")}
derived = json.load(open(os.path.join(HERE, "derived.json")))
DATA = {n: json.load(open(os.path.join(ROOT, f"data/{n}.json"))) for n in
        ["train_hindi_45h", "train_english_45h", "train_marathi_15h", "train_odia_15h", "train_kannada_15h"] +
        [f"test_{t}_{l}" for t in ["fleurs", "kathbath"] for l in ["hindi", "marathi", "odia", "kannada"]]}
CFG_P = json.load(open(os.path.join(ROOT, "runs/P-hindi/train_config.json")))
CFG_T = json.load(open(os.path.join(ROOT, "runs/H-odia/train_config.json")))
NAME = {"hindi": "Hindi", "marathi": "Marathi", "kannada": "Kannada", "odia": "Odia", "english": "English"}
TARGETS = ["marathi", "odia", "kannada"]
TS = {"fleurs": "FLEURS", "kathbath": "Kathbath"}


def r1(v):
    return Decimal(repr(float(v))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def f1(v):
    return f"{r1(v)}"


def sg(v):
    q = r1(v)
    return f"{'+' if q > 0 else '−' if q < 0 else ''}{abs(q)}"


def pl(v):
    q = r1(v)
    return f"{'−' if q < 0 else ''}{abs(q)}"


def M(run, ts="fleurs", col="WER_clean"):
    return float(next(r for r in master if r["run_id"] == run and r["test_set"] == ts)[col])


def G(lang, ts, key, metric="WER"):
    r = next(r for r in gains if r["language"] == lang and r["test_set"] == ts and r["gain"] == key and r["metric"] == metric)
    return float(r["points"]), float(r["ci_low"]), float(r["ci_high"]), r["significant"] == "True"


def ci_txt(p, lo, hi):
    return f"{sg(p)} [{pl(lo)}, {pl(hi)}]"


# ======================================================================= the team's text (from the paper)
CITE = {
    "conneau2021xlsr": ("Conneau et al., 2021", 2021), "babu2022xlsr": ("Babu et al., 2022", 2022),
    "radford2023whisper": ("Radford et al., 2023", 2023), "pratap2024mms": ("Pratap et al., 2024", 2024),
    "pillai2026multistage": ("Pillai et al., 2026", 2026), "rouditchenko2023unseen": ("Rouditchenko et al., 2023", 2023),
    "song2024lorawhisper": ("Song et al., 2024", 2024), "hu2022lora": ("Hu et al., 2022", 2022),
    "xu2024rehearsalfree": ("Xu et al., 2024", 2024), "ferraz2024distilwhisper": ("Ferraz et al., 2024", 2024),
    "houlsby2019adapters": ("Houlsby et al., 2019", 2019), "pfeiffer2020madx": ("Pfeiffer et al., 2020", 2020),
    "javed2024indicvoices": ("Javed et al., 2024", 2024), "javed2023indicsuperb": ("Javed et al., 2023", 2023),
    "bhogale2023vistaar": ("Bhogale et al., 2023", 2023), "conneau2023fleurs": ("Conneau et al., 2023", 2023),
    "pineiro2024weighted": ("Piñeiro-Martín et al., 2024", 2024), "panayotov2015librispeech": ("Panayotov et al., 2015", 2015),
    "ardila2020commonvoice": ("Ardila et al., 2020", 2020), "wolf2020transformers": ("Wolf et al., 2020", 2020),
    "peft2022": ("Mangrulkar et al., 2022", 2022), "bisani2004bootstrap": ("Bisani & Ney, 2004", 2004),
    "mlx2023": ("Hannun et al., 2023", 2023),
}
CAPS = json.load(open(os.path.join(HERE, "captions.json"))) if os.path.exists(os.path.join(HERE, "captions.json")) else {}
CAPS.setdefault("labels", {})


def ref(label):
    kind, num = CAPS["labels"].get(label, ["Table" if label.startswith("tab") else "Fig.", "??"])
    return f"{kind} {num}"


REF_LABEL = {"tab:setup": "tab:setup", "fig:arch": "fig:pipeline", "tab:comparison": "tab:yearwise", "fig:gains": "fig:gains"}
INLINE_MATH = {r"$\alpha$": "α", r"$10^{-3}$": "10^{−3}", r"$W_0$": "W_{0}", r"$r_L$": "r_{L}", r"$A$": "A", r"$B$": "B",
               r"$S$": "S", r"$D$": "D", r"$I$": "I", r"$N$": "N", r"$s$": "s"}


def clean(t):
    t = re.sub(r"\\cite\{([^}]*)\}", lambda m: "(" + "; ".join(sorted(CITE[k.strip()][0] for k in m.group(1).split(","))) + ")", t)
    t = re.sub(r"\\ref\{([^}]*)\}", lambda m: ref(REF_LABEL[m.group(1)]), t)
    t = t.replace("Table~Table", "Table").replace("Fig.~Fig.", "Fig.").replace("Table Table", "Table").replace("Fig. Fig.", "Fig.")
    for k, v in INLINE_MATH.items():
        t = t.replace(k, v)
    t = re.sub(r"\\textbf\{([^}]*)\}", r"**\1**", t)
    t = re.sub(r"\\(emph|textit|texttt)\{([^}]*)\}", r"\2", t)
    t = re.sub(r"\\(?=\s)", " ", t)
    t = t.replace("~", " ").replace("\\%", "%").replace("\\,", " ").replace("\\&", "&")
    t = t.replace("\\'{i}", "í").replace("\\~{n}", "ñ")
    t = t.replace("---", "—").replace("--", "–").replace("``", "“").replace("''", "”")
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace("this paper", "this report").replace("This paper", "This report")
    assert "\\" not in t and "$" not in t, t[:120]
    return t


def parse_paper():
    s = open(os.path.join(ROOT, "report/paper/revised_wording.tex"), encoding="utf-8").read()
    abstract = clean(s[s.index(r"\begin{abstract}") + 16:s.index(r"\end{abstract}")])
    keywords = clean(s[s.index(r"\begin{IEEEkeywords}") + 20:s.index(r"\end{IEEEkeywords}")])
    body = s[s.index(r"\section{Introduction}"):s.index(r"\begin{thebibliography}")]
    body = "\n".join(re.sub(r"(?<!\\)%.*$", "", ln) for ln in body.split("\n"))
    for env in ["figure", "table*", "table"]:
        b, e = "\\begin{" + env + "}", "\\end{" + env + "}"
        while b in body:
            i = body.index(b)
            body = body[:i] + body[body.index(e, i) + len(e):]
    body = re.sub(r"\\input\{[^}]*\}", "", body)
    out, sec, sub = {}, None, None
    for tok in re.split(r"(\\(?:section|subsection)\{[^}]*\})", body):
        m = re.match(r"\\(section|subsection)\{([^}]*)\}", tok)
        if m:
            if m.group(1) == "section":
                sec, sub = m.group(2), None
            else:
                sub = m.group(2)
            continue
        blocks = []
        pos = 0
        for em in re.finditer(r"\\begin\{(equation\*?|enumerate|quote)\}(.*?)\\end\{\1\}", tok, re.S):
            for para in re.split(r"\n\s*\n", tok[pos:em.start()]):
                if para.strip():
                    blocks.append(("p", clean(para)))
            kind, inner = em.group(1), em.group(2)
            if kind.startswith("equation"):
                lab = re.search(r"\\label\{([^}]*)\}", inner)
                blocks.append(("eq", lab.group(1) if lab else "eq:lmax"))
            elif kind == "enumerate":
                blocks.append(("list", [clean(x) for x in inner.split(r"\item") if x.strip()]))
            else:
                blocks.append(("quote", clean(inner)))
            pos = em.end()
        for para in re.split(r"\n\s*\n", tok[pos:]):
            if para.strip():
                blocks.append(("p", clean(para)))
        # a sentence that continues after an equation ("where W0 is ...") joins the equation block
        out[(sec, sub)] = blocks
    return abstract, keywords, out


ABSTRACT, KEYWORDS, PAPER = parse_paper()
EQS = {"eq:lora": "W = W_{0} + (α / r) · BA,     B ∈ ℝ^{d × r},  A ∈ ℝ^{r × k}",
       "eq:lmax": "L_{max} = min(440, 10 + ⌈1.5 · r_{L} · s⌉)",
       "eq:wer": "WER = (S + D + I) / N × 100",
       "eq:script": "Script = (letters in the target script ÷ all letters) × 100",
       "eq:rtf": "RTF = t_{decode} / t_{audio}",
       "eq:gain": "G_{p}(t) = WER_{direct}(t) − WER_{p→t}(t),     p ∈ {Hi, En}",
       "eq:delta": "Δ(t) = G_{Hi}(t) − G_{En}(t) = WER_{En→t} − WER_{Hi→t}",
       "eq:interaction": "I(t_{1}, t_{2}) = Δ(t_{1}) − Δ(t_{2})"}

# ======================================================================= document setup
doc = Document()
doc.core_properties.title = TITLE
doc.core_properties.author = ", ".join(n for n, _ in TEAM)


def set_rfonts(rpr, name=TNR):
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in list(rf.attrib):
        if a.endswith("Theme"):
            del rf.attrib[a]
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)


def style(name, size, bold=False, italic=False, align=None, before=0, after=6, spacing=1.5, keep=False, pbb=False, underline=False):
    st = doc.styles[name]
    st.font.name, st.font.size, st.font.bold, st.font.italic = TNR, Pt(size), bold, italic
    st.font.underline = underline
    st.font.color.rgb = BLACK
    rpr = st.element.get_or_add_rPr()
    set_rfonts(rpr)
    col = rpr.find(qn("w:color"))
    if col is not None:
        for a in list(col.attrib):
            if a.endswith("themeColor") or a.endswith("themeShade") or a.endswith("themeTint"):
                del col.attrib[a]
    pf = st.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(before), Pt(after), spacing
    pf.keep_with_next, pf.page_break_before, pf.widow_control = keep, pbb, True
    if align is not None:
        pf.alignment = align
    return st


style("Normal", 12, after=6)
style("Heading 1", 16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=18, spacing=1.15, keep=True, pbb=True)
style("Heading 2", 14, bold=True, before=18, after=8, spacing=1.15, keep=True)
style("Heading 3", 12, bold=True, before=12, after=6, spacing=1.15, keep=True)
style("Caption", 11, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=12, spacing=1.0)
for ls in ("List Bullet", "List Number"):
    style(ls, 12, after=4)

sec0 = doc.sections[0]


def page_setup(sec):
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin = Cm(3.81), Cm(2.54), Cm(2.54), Cm(2.54)
    sec.footer_distance, sec.header_distance = Cm(1.25), Cm(1.25)


page_setup(sec0)


# ======================================================================= helpers
def runs_into(p, text, size=None, bold=None, italic=None, color=None, font=TNR):
    """**bold**, _{sub}, ^{sup} markup."""
    for tok in re.split(r"(\*\*.+?\*\*|_\{[^}]*\}|\^\{[^}]*\})", text):
        if not tok:
            continue
        sub = sup = False
        b = bold
        if tok.startswith("**"):
            tok, b = tok[2:-2], True
        elif tok.startswith("_{"):
            tok, sub = tok[2:-1], True
        elif tok.startswith("^{"):
            tok, sup = tok[2:-1], True
        r = p.add_run(tok)
        r.font.name = font
        set_rfonts(r._element.get_or_add_rPr(), font)
        if size:
            r.font.size = Pt(size)
        if b is not None:
            r.font.bold = b
        if italic is not None:
            r.font.italic = italic
        if color is not None:
            r.font.color.rgb = color
        r.font.subscript, r.font.superscript = sub or None, sup or None
    return p


def P(text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=None, bold=None, italic=None, color=None, after=None, before=None,
      spacing=None, keep=False, style_name=None, indent=None):
    p = doc.add_paragraph(style=style_name)
    p.alignment = align
    if text:
        runs_into(p, text, size, bold, italic, color)
    pf = p.paragraph_format
    if after is not None:
        pf.space_after = Pt(after)
    if before is not None:
        pf.space_before = Pt(before)
    if spacing is not None:
        pf.line_spacing = spacing
    if keep:
        pf.keep_with_next = True
    if indent is not None:
        pf.left_indent = Cm(indent)
    return p


def mixed(parts, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=None, after=None, spacing=None):
    """parts: list of (text, {bold, italic, color})."""
    p = doc.add_paragraph()
    p.alignment = align
    for text, o in parts:
        runs_into(p, text, size, o.get("bold"), o.get("italic"), o.get("color"))
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if spacing is not None:
        p.paragraph_format.line_spacing = spacing
    return p


def bullets(items, numbered=False):
    for k, it in enumerate(items, 1):
        if numbered:
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent, pf.first_line_indent = Cm(0.75), Cm(-0.75)
            pf.tab_stops.add_tab_stop(Cm(0.75))
            pf.space_after = Pt(4)
            runs_into(p, f"{k}.\t")
        else:
            p = doc.add_paragraph(style="List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if isinstance(it, str):
            runs_into(p, it)
        else:
            for text, o in it:
                runs_into(p, text, None, o.get("bold"), o.get("italic"), o.get("color"))


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def heading(text, level):
    h = doc.add_heading(level=level)
    runs_into(h, text)
    return h


def field_run(p, instr, size=None):
    for kind in ("begin", None, "end"):
        r = p.add_run()
        if size:
            r.font.size = Pt(size)
        if kind is None:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = f" {instr} "
            r._element.append(it)
        else:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r._element.append(fc)


def footer_page_number(sec, fmt):
    sec.footer.is_linked_to_previous = False
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field_run(fp, "PAGE", 12)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), fmt)
    pg.set(qn("w:start"), "1")
    sp = sec._sectPr
    for old in sp.findall(qn("w:pgNumType")):
        sp.remove(old)
    anchor = next((sp.find(qn(t)) for t in ("w:cols", "w:formProt", "w:vAlign", "w:noEndnote", "w:titlePg", "w:textDirection",
                                            "w:bidi", "w:rtlGutter", "w:docGrid") if sp.find(qn(t)) is not None), None)
    if anchor is not None:
        anchor.addprevious(pg)
    else:
        sp.append(pg)


def shade(cell, fill):
    tcPr = cell._element.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), fill)
    after = next((tcPr.find(qn(t)) for t in ("w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark")
                  if tcPr.find(qn(t)) is not None), None)
    if after is not None:
        after.addprevious(sh)
    else:
        tcPr.append(sh)


def no_borders(table):
    tblPr = table._element.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "nil")
        b.append(e)
    after = next((tblPr.find(qn(t)) for t in ("w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription")
                  if tblPr.find(qn(t)) is not None), None)
    if after is not None:
        after.addprevious(b)
    else:
        tblPr.append(b)


fig_list, tab_list, labels = [], [], {}
CH = [""]
counters = {}


def caption(kind, label, text):
    counters[(kind, CH[0])] = counters.get((kind, CH[0]), 0) + 1
    num = f"{CH[0]}.{counters[(kind, CH[0])]}"
    word = "Fig." if kind == "fig" else "Table"
    labels[label] = [word, num]
    p = doc.add_paragraph(style="Caption")
    runs_into(p, f"{word} {num}: ", bold=True)
    runs_into(p, text)
    (fig_list if kind == "fig" else tab_list).append([num, text, label])
    if kind == "tab":
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
    return p


_FONTS = {}


def word_cm(word, bold, size):
    """Printed width of one unbreakable word in Times New Roman, in cm."""
    key = (bold, size)
    if key not in _FONTS:
        name = "Times New Roman Bold.ttf" if bold else "Times New Roman.ttf"
        _FONTS[key] = ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{name}", int(size * 20))
    return _FONTS[key].getlength(word) / 20 * 2.54 / 72


def fit_widths(data, widths, size, header, bold_first, indic_cols):
    """Widen any column whose longest word would be split across lines, taking the space from columns with slack."""
    need = []
    for ci in range(len(widths)):
        m = 0.0
        for ri, row in enumerate(data):
            head = ri == 0 and header
            if ci in indic_cols and not head:
                continue
            val = row[ci]
            text = val if isinstance(val, str) else "".join(t for t, _ in val)
            for piece in re.split(r"\s+|(?<=[-/])", text):
                m = max(m, word_cm(piece, head or (bold_first and ci == 0), size))
        need.append(m + 0.38 + 0.1)   # Table Grid cell margins are 0.19 cm a side
    w = list(widths)
    for _ in range(20):
        short = [i for i in range(len(w)) if w[i] < need[i] - 1e-6]
        if not short:
            break
        deficit = sum(need[i] - w[i] for i in short)
        for i in short:
            w[i] = need[i]
        slack = {i: w[i] - need[i] for i in range(len(w)) if i not in short and w[i] > need[i]}
        if not slack:
            break
        tot = sum(slack.values())
        for i, sl in slack.items():
            w[i] -= min(deficit, tot) * sl / tot
    return w


def table_height_cm(data, widths, size):
    """Rough printed height of a table: wrapped lines per row at single spacing, plus cell padding."""
    line = size * 1.2 / 72 * 2.54
    total = 0.0
    for row in data:
        lines = 1
        for ci, val in enumerate(row):
            text = val if isinstance(val, str) else "".join(t for t, _ in val)
            lines = max(lines, -(-word_cm(text, False, size) // max(widths[ci] - 0.45, 0.5)) or 1)
        total += lines * line + 0.1
    return total


def table(label, title, data, widths, align=None, size=10.5, bold_first=False, header=True, notes=None, indic_cols=()):
    widths = fit_widths(data, widths, size, header, bold_first, indic_cols)
    body = doc.element.body
    last = body[-2] if body[-1].tag == qn("w:sectPr") else body[-1]
    if last.tag == qn("w:p"):
        prev = Paragraph(last, doc._body)
        if prev.style.name == "Normal" and 0 < len(prev.text) < 300:
            prev.paragraph_format.keep_with_next = True
    if label in BREAKS:
        start = None
        e = last
        while e is not None and e.tag == qn("w:p"):
            para = Paragraph(e, doc._body)
            if not (para.paragraph_format.keep_with_next or (para.paragraph_format.keep_with_next is None
                                                             and para.style.paragraph_format.keep_with_next)):
                break
            start, e = para, e.getprevious()
    cp = caption("tab", label, title)
    if label in BREAKS:
        (start or cp).paragraph_format.page_break_before = True
    if table_height_cm(data, widths, size) > 18.0:
        # Pages will not split a table whose caption must stay with it; let a long table start under its caption
        cp.paragraph_format.keep_with_next = False
    t = doc.add_table(rows=len(data), cols=len(widths))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for ri, row in enumerate(data):
        tr = t.rows[ri]
        if ri == 0 and header:
            trPr = tr._tr.get_or_add_trPr()
            h = OxmlElement("w:tblHeader")
            h.set(qn("w:val"), "true")
            trPr.append(h)
        cant = OxmlElement("w:cantSplit")
        tr._tr.get_or_add_trPr().append(cant)
        for ci, val in enumerate(row):
            c = t.cell(ri, ci)
            c.width = Cm(widths[ci])
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(0)
            a = (align or ["l"] * len(widths))[ci]
            p.alignment = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER, "r": WD_ALIGN_PARAGRAPH.RIGHT}[a]
            is_head = ri == 0 and header
            if is_head:
                shade(c, "D9D9D9")
            parts = [(val, {})] if isinstance(val, str) else val
            for text, o in parts:
                font = "Nirmala UI" if ci in indic_cols and not is_head else TNR
                runs_into(p, text, size, o.get("bold", is_head or (bold_first and ci == 0)), o.get("italic"), o.get("color"), font=font)
    for ci, w in enumerate(widths):
        t.columns[ci].width = Cm(w)
    if notes:
        P(notes, align=WD_ALIGN_PARAGRAPH.LEFT, size=10, italic=True, spacing=1.0, before=4, after=10)
    else:
        P("", spacing=1.0, after=4)
    return t


def figure(label, path, title, width=TEXT_W, note=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(6)
    p.add_run().add_picture(path, width=Cm(width))
    cp = caption("fig", label, title)
    if note:
        cp.paragraph_format.keep_with_next = True
        cp.paragraph_format.space_after = Pt(2)
        P(note, align=WD_ALIGN_PARAGRAPH.CENTER, size=10, italic=True, spacing=1.0, after=12)


eq_counter = [0]


def equation(label):
    eq_counter[0] += 1
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.tab_stops.add_tab_stop(Cm(TEXT_W / 2), WD_TAB_ALIGNMENT.CENTER)
    pf.tab_stops.add_tab_stop(Cm(TEXT_W), WD_TAB_ALIGNMENT.RIGHT)
    pf.space_before, pf.space_after = Pt(6), Pt(6)
    runs_into(p, "\t")
    runs_into(p, EQS[label], italic=True)
    runs_into(p, f"\t(3.{eq_counter[0]})")


def paper(sec, sub=None, start=0, end=None):
    """Emit the team's paragraphs from one paper subsection."""
    for kind, val in PAPER[(sec, sub)][start:end]:
        if kind == "p":
            if val.startswith("where "):
                P(val, after=6)
            else:
                P(val)
        elif kind == "eq":
            equation(val)
        elif kind == "list":
            bullets(val, numbered=True)
        elif kind == "quote":
            P(val, align=WD_ALIGN_PARAGRAPH.LEFT, italic=True, indent=1.0)


def red(text):
    return (text, {"color": RED})


def pg(key):
    return str(PAGES.get(key, "00"))


# ======================================================================= front matter (no page numbers)
LOGO = os.path.join(HERE, "assets", "rvu_logo.png")


def logo(width=6.2, new_page=False):
    p = doc.add_paragraph()
    p.paragraph_format.page_break_before = new_page
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    p.add_run().add_picture(LOGO, width=Cm(width))


def title_block():
    logo()
    C = WD_ALIGN_PARAGRAPH.CENTER
    P("School of Computer Science and Engineering", C, 16, True, spacing=1.0, after=6)
    P("November 2026", C, 12, spacing=1.0, after=20)
    P(TITLE.upper(), C, 20, True, spacing=1.15, after=18)
    P("Submitted in partial fulfillment for the award of the degree of", C, 14, italic=True, spacing=1.0, after=8)
    P(DEGREE, C, 22, True, spacing=1.0, after=4)
    P("in Computer Science and Engineering", C, 14, spacing=1.0, after=14)
    P("by", C, 14, italic=True, spacing=1.0, after=8)
    for n, u in TEAM:
        P(f"{n.upper()} ({u})", C, 16, True, spacing=1.0, after=4)
    P("Guided by", C, 14, italic=True, spacing=1.0, before=12, after=6)
    P(GUIDE.upper(), C, 16, True, spacing=1.0, after=4)
    p = mixed([red(GUIDE_DESIG.upper()), (", SOCSE, RV UNIVERSITY", {})], C, 16, spacing=1.0)
    for r in p.runs:
        r.font.bold = True


title_block()          # cover page
page_break()
title_block()          # title page
page_break()

# certificate
logo(4.8)
C = WD_ALIGN_PARAGRAPH.CENTER
P("School of Computer Science and Engineering", C, 16, True, spacing=1.0, after=4)
P("RV University", C, 12, spacing=1.0, after=2)
P("RV Vidyaniketan, 8th Mile, Mysore Road, Bengaluru, Karnataka, India - 560059", C, 12, spacing=1.0, after=18)
P("CERTIFICATE", C, 16, True, spacing=1.0, after=14)
names = ", ".join(f"{n} ({u})" for n, u in TEAM[:-1]) + f" and {TEAM[-1][0]} ({TEAM[-1][1]})"
P(f"This is to certify that the project work titled “{TITLE}” is performed by {names}, bonafide students of {DEGREE} "
  f"at the School of Computer Science and Engineering, RV University, Bengaluru in partial fulfillment for the award of "
  f"the degree {DEGREE} in Computer Science & Engineering, during the Academic year 2026-2027.", after=14)
sig = doc.add_table(rows=6, cols=3)
no_borders(sig)
cols = [[(GUIDE, {})], [("Dr. Rashmi S", {})], [(DEAN, {})]]
lines = [cols, [[("Guide", {})], [("Program Director", {})], [("Dean", {})]],
         [[red(GUIDE_DESIG)], [("B.Tech (Hons.)", {})], [("SoCSE", {})]],
         [[("SoCSE", {})], [("SoCSE", {})], [("RV University", {})]],
         [[("RV University", {})], [("RV University", {})], [("", {})]],
         [[("Date:", {})], [("Date:", {})], [("Date:", {})]]]
for ri, line in enumerate(lines):
    for ci, parts in enumerate(line):
        c = sig.cell(ri, ci)
        c.width = Cm(TEXT_W / 3)
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        for text, o in parts:
            runs_into(p, text, 12, ri == 0, color=o.get("color"))
P("", after=6)
sig2 = doc.add_table(rows=4, cols=2)
no_borders(sig2)
for ri, (a, b) in enumerate([("", "Signature of the Guide"), ("Name of the Examiner", "Signature of Examiner"),
                              ("1.", "1."), ("2.", "2.")]):
    for ci, text in enumerate((a, b)):
        c = sig2.cell(ri, ci)
        c.width = Cm(TEXT_W / 2)
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(8)
        runs_into(p, text, 12)


# declaration
logo(new_page=True)
p = P("DECLARATION", C, 14, True, spacing=1.0, after=24)
p.runs[0].font.underline = True
P(f"We hereby declare that the thesis entitled “{TITLE}” submitted by us, for the award of the degree {DEGREE} in RV University "
  f"is a record of bonafide work carried out by us under the supervision of ", after=12).add_run()
doc.paragraphs[-1].runs[-1].text = ""
runs_into(doc.paragraphs[-1], GUIDE)
runs_into(doc.paragraphs[-1], ".")
P("We further declare that the work reported in this thesis has not been submitted and will not be submitted, either in part or "
  "in full, for the award of any other degree or diploma in this institute or any other institute or university.", after=36)
P("Place: Bangalore", WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0, after=4)
P("Date:", WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0, after=36)
dec = doc.add_table(rows=2, cols=2)
no_borders(dec)
for i, (n, u) in enumerate(TEAM):
    c = dec.cell(i // 2, i % 2)
    c.width = Cm(TEXT_W / 2)
    p = c.paragraphs[0]
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(30)
    runs_into(p, "\n\n")
    runs_into(p, f"{n}\n{u}\n", 12, True)
    runs_into(p, "Signature of the Candidate", 12)

# ======================================================================= front matter (roman)
def tiny_break():
    """python-docx ends a section with an empty paragraph; make it 1 pt so it cannot push a blank page."""
    p = doc.paragraphs[-1]
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(0), Pt(1)
    pf.line_spacing_rule = 4   # exact
    ppr = p._p.get_or_add_pPr()
    rpr, sz = OxmlElement("w:rPr"), OxmlElement("w:sz")
    sz.set(qn("w:val"), "2")
    rpr.append(sz)
    sect = ppr.find(qn("w:sectPr"))
    if sect is not None:
        sect.addprevious(rpr)
    else:
        ppr.append(rpr)


sec1 = doc.add_section(WD_SECTION.NEW_PAGE)
tiny_break()
page_setup(sec1)
footer_page_number(sec1, "lowerRoman")


def front_heading(text, underline=True):
    p = P(text, C, 14, True, spacing=1.0, after=18)
    p.runs[0].font.underline = underline
    return p


front_heading("ABSTRACT")
P(ABSTRACT)
mixed([("Keywords: ", {"bold": True}), (KEYWORDS, {})], after=6)
page_break()

front_heading("ACKNOWLEDGEMENT")
mixed([("It is our pleasure to express with deep sense of gratitude to ", {}), (GUIDE, {}), (", ", {}), red(GUIDE_DESIG),
       (", School of Computer Science and Engineering, RV University, for constant guidance, continual encouragement and "
        "understanding throughout this project. Our association has not been confined to academics only; it has been a great "
        "opportunity for us to work with an expert in the field of speech and language processing.", {})])
P(f"We would like to express our gratitude to Prof Dr Ram Kumar Kakani, Vice Chancellor, RV University, and Prof {DEAN}, "
  "Dean, SoCSE, RV University, for providing us with an environment to work in and for their inspiration during the tenure of "
  "the course.")
P("We express our whole-hearted thanks to Dr. Rashmi S, Program Director, B.Tech (Hons.), SoCSE, RV University, and to all "
  "teaching staff and members of our university for their enthusiasm and timely encouragement, which helped us acquire the "
  "knowledge needed to complete this work. We would like to thank our parents for their support.")
P("It is indeed a pleasure to thank our friends who encouraged us to take up and complete this task. Last but not least, we "
  "express our gratitude and appreciation to all those who have helped us directly or indirectly toward the successful "
  "completion of this project.", after=10)
P("Place: Bangalore", WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0, after=4)
P("Date:", WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0, after=4)
for n, u in TEAM:
    P(f"{n} ({u})", WD_ALIGN_PARAGRAPH.RIGHT, bold=True, spacing=1.0, after=0)
page_break()

# ---- contents: a real TOC field whose shown result is the static list below (Word: right-click > Update Field)
TOC_ENTRIES = []   # (level, text, page_key) - filled while building chapters, written on the second pass
toc_anchor = front_heading("CONTENTS", underline=False)
toc_paras_start = len(doc.paragraphs)


def toc_line(text, page, level, bold=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing, pf.space_after = 1.0, Pt(4 if level == 1 else 2)
    pf.left_indent = Cm(0 if level == 1 else 0.8)
    pf.tab_stops.add_tab_stop(Cm(TEXT_W), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    if level == 1:
        pf.space_before = Pt(6)
    runs_into(p, text, 12 if level == 1 else 11.5, bold)
    runs_into(p, f"\t{page}", 12 if level == 1 else 11.5, bold)
    return p


PLAN = json.load(open(os.path.join(HERE, "toc_plan.json"))) if os.path.exists(os.path.join(HERE, "toc_plan.json")) else []
if PLAN:
    PLAN = [[1, "CONTENTS", "front:contents"], [1, "LIST OF TABLES", "front:lot"], [1, "LIST OF FIGURES", "front:lof"],
            [1, "LIST OF ACRONYMS", "front:acr"]] + PLAN
for level, text, key in PLAN:
    toc_line(text, pg(key), level, bold=level == 1)
page_break()

lot_heading = front_heading("LIST OF TABLES", underline=False)
def list_table(entries, word, hang):
    """List of tables or figures as a borderless two-column table, so a wrapped title never pushes its
    page number onto a line of its own (Word and Pages agree on this layout)."""
    if not entries:
        return
    w0, w1 = TEXT_W - 1.1, 1.1
    t = doc.add_table(rows=len(entries), cols=2)
    no_borders(t)
    t.autofit = False
    for i, (num, text, label) in enumerate(entries):
        c0, c1 = t.cell(i, 0), t.cell(i, 1)
        c0.width, c1.width = Cm(w0), Cm(w1)
        p = c0.paragraphs[0]
        pf = p.paragraph_format
        pf.line_spacing, pf.space_after = 1.0, Pt(3)
        pf.left_indent, pf.first_line_indent = Cm(hang), Cm(-hang)
        pf.tab_stops.add_tab_stop(Cm(hang))
        pf.tab_stops.add_tab_stop(Cm(w0 - 0.4), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        runs_into(p, f"{word} {num}\t", 11.5, True)
        runs_into(p, f"{text}\t", 11.5)
        q = c1.paragraphs[0]
        q.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        q.paragraph_format.line_spacing, q.paragraph_format.space_after = 1.0, Pt(3)
        runs_into(q, str(pg(label)), 11.5)
        c1.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
    for ci, w in enumerate((w0, w1)):
        t.columns[ci].width = Cm(w)


list_table(CAPS.get("tabs", []), "Table", 2.2)
page_break()
lof_heading = front_heading("LIST OF FIGURES", underline=False)
list_table(CAPS.get("figs", []), "Fig.", 1.9)
page_break()
front_heading("LIST OF ACRONYMS", underline=False)
ACR = [("ASR", "Automatic Speech Recognition"), ("BPE", "Byte-Pair Encoding"), ("CER", "Character Error Rate"),
       ("CI", "Confidence Interval"), ("FLEURS", "Few-shot Learning Evaluation of Universal Representations of Speech"),
       ("fp16", "16-bit floating point"), ("fp32", "32-bit floating point"), ("GB", "Gigabyte"), ("GPU", "Graphics Processing Unit"),
       ("LoRA", "Low-Rank Adaptation"), ("MB", "Megabyte"), ("MLX", "Apple's machine-learning framework for Apple silicon"),
       ("MMS", "Massively Multilingual Speech"), ("MPS", "Metal Performance Shaders (PyTorch's Apple GPU backend)"),
       ("NFC", "Unicode Normalization Form C (canonical composition)"), ("PEFT", "Parameter-Efficient Fine-Tuning"),
       ("RQ", "Research Question"), ("RTF", "Real-Time Factor"), ("SDPA", "Scaled Dot-Product Attention"),
       ("SoCSE", "School of Computer Science and Engineering"), ("UTF-8", "8-bit Unicode Transformation Format"),
       ("WER", "Word Error Rate"), ("XLS-R", "Cross-lingual Speech Representations (wav2vec 2.0 model family)")]
t = doc.add_table(rows=len(ACR), cols=2)
no_borders(t)
for i, (a, b) in enumerate(ACR):
    for ci, (text, w) in enumerate(((a, 3.0), (b, TEXT_W - 3.0))):
        c = t.cell(i, ci)
        c.width = Cm(w)
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.0
        runs_into(p, text, 12, ci == 0)

# ======================================================================= chapters (arabic)
sec2 = doc.add_section(WD_SECTION.NEW_PAGE)
tiny_break()
page_setup(sec2)
footer_page_number(sec2, "decimal")
plan = []


def chapter(n, title, first=False):
    CH[0] = str(n)
    h = doc.add_heading(level=1)
    runs_into(h, f"CHAPTER {n}", 12)
    h.runs[-1].add_break()
    runs_into(h, title.upper(), 16)
    if first:
        h.paragraph_format.page_break_before = False
    plan.append((1, f"CHAPTER {n}: {title.upper()}", f"ch:{n}"))


def section(num, title):
    heading(f"{num} {title.upper()}", 2)
    plan.append((2, f"{num} {title.upper()}", f"sec:{num}"))


def sub(num, title):
    heading(f"{num} {title.upper()}", 3)


YEARWISE = [
    ("2019", "Houlsby et al.", "Bottleneck adapter modules", "Parameter-efficient transfer is competitive with full fine-tuning.", "Text-only; no speech or script considerations."),
    ("2020", "Ardila et al.", "Common Voice corpus", "Volunteer-recorded multilingual speech at scale.", "Dataset; no transfer study. Removed from Hugging Face by the time of our experiments."),
    ("2020", "Pfeiffer et al.", "MAD-X separable language/task adapters", "Modular adapters enable transfer to unseen languages.", "Text modality; does not address acoustic transfer."),
    ("2021", "Conneau et al.", "XLSR-53, cross-lingual wav2vec 2.0", "Shared cross-lingual representations outperform monolingual pre-training.", "Transfer studied in aggregate; no pairwise source–target analysis."),
    ("2022", "Babu et al.", "XLS-R, up to 2B parameters, 128 languages", "Scaling cross-lingual self-supervision improves low-resource ASR.", "Very large compute requirement; family effects not isolated."),
    ("2022", "Hu et al.", "LoRA low-rank adaptation", "Comparable quality while training under 1% of parameters.", "Not originally evaluated for speech or cross-lingual transfer."),
    ("2023", "Radford et al.", "Whisper, weakly-supervised encoder–decoder (680K hours)", "Large-scale weak supervision yields robust zero-shot ASR.", "Closed 99-language token set; Odia absent; highly uneven per-language quality."),
    ("2023", "Rouditchenko et al.", "Fine-tuning XLS-R vs. Whisper (13 unseen, 18 seen languages)", "Pre-training hours per language and per family predict adaptation quality.", "Family exposure is observational, not experimentally manipulated."),
    ("2023", "Bhogale et al.", "Vistaar benchmarks; IndicWhisper (59 benchmarks, 12 languages, 10.7K hours)", "Lowest WER on 39/59 benchmarks; rankings vary across benchmarks.", "Joint multilingual training; pairwise transfer not isolated."),
    ("2023", "Javed et al.", "IndicSUPERB / Kathbath", "Standardized evaluation across Indian languages.", "Benchmark rather than adaptation methodology."),
    ("2023", "Conneau et al.", "FLEURS parallel speech benchmark (102 languages)", "A shared test set for cross-lingual comparison.", "Read speech only."),
    ("2024", "Pratap et al.", "MMS, 1000+ language ASR", "Language coverage can be extended by an order of magnitude.", "Supervision drawn from a narrow domain; limited generality."),
    ("2024", "Song et al.", "LoRA-Whisper for multilingual ASR", "Mitigates language interference; language similarity aids new-language extension.", "Similarity exploited heuristically, not measured as an independent variable."),
    ("2024", "Xu et al.", "LoRA-based rehearsal-free extension of Whisper", "New languages can be added without rehearsal data.", "Focus on forgetting rather than transfer mechanism."),
    ("2024", "Ferraz et al.", "DistilWhisper with language-specific experts", "Distillation retains per-language capability at reduced size.", "Compression-oriented; no pivot-language analysis."),
    ("2024", "Javed et al.", "IndicVoices corpus (23.7K hours, 51K speakers, 22 languages)", "Large-scale spontaneous Indian speech resource.", "Dataset contribution; no transfer-strategy study."),
    ("2024", "Piñeiro-Martín et al.", "Weighted cross-entropy for imbalanced multilingual ASR", "Objective reweighting improves low-resource languages.", "Addresses optimization, not evaluation normalization."),
    ("2026", "Pillai et al.", "Multistage fine-tuning, Whisper via Tamil pivot (Malasar, ≈4h36m)", "51.9% WER, 4.5% absolute gain over direct fine-tuning; 47.3% after punctuation removal.", "Single pivot–target pair; relatedness claim not tested against a distant-language control."),
]

# ---------------------------------------------------------------- Chapter 1
chapter(1, "Introduction", first=True)
section("1.1", "Introduction")
paper("Introduction", "Background and Context")
section("1.2", "Motivation")
paper("Introduction", "Motivation and Research Gap")
section("1.3", "Problem Statement")
paper("Problem Statement")
section("1.4", "Objectives")
paper("Identified Gaps and Proposed Direction", "Research Questions")
P(f"The project objectives follow from these questions. {ref('tab:rq')} maps each question to the experiment that answers it.")
bullets(["Test whether the gain from multistage fine-tuning comes from pivot relatedness or from the extra data, using a Hindi "
         "pivot and an English pivot of equal size (45 hours, 2,000 steps).",
         "Compare the Hindi-pivot gain across Marathi, Odia (Indo-Aryan) and Kannada (Dravidian) on two independent test sets.",
         "Measure which borrowed language token works for Odia, which has no Whisper token.",
         "Quantify how normalization and scoring rules change WER and the ranking of methods.",
         "Deploy the trained models offline on a laptop and measure size, speed and accuracy."], numbered=True)
table("tab:rq", "Research questions mapped to experiments and measures", [
    ["Question", "Experiment", "Measure"],
    ["Main: relatedness or data quantity?", "Hindi and English pivots of equal size (45 h, 2,000 steps), then each target", "Δ = G(Hindi) − G(English), 95% CI"],
    ["RQ1: Indo-Aryan or Dravidian?", "The same runs across Marathi, Odia and Kannada", "Difference in Δ between targets"],
    ["RQ2: which borrowed token for Odia?", "Odia under the Bengali, Assamese and Hindi tokens, untrained and trained", "WER, CER, script validity"],
    ["RQ3: do scoring rules matter?", "Every run scored raw, normalized and with Whisper's normalizer", "WER under each rule; method ranking"],
    ["Deployment", "Merged models in MLX at fp16 and 4-bit", "Size, real-time factor, WER, CER"],
], [4.3, 6.0, 4.35], ["l", "l", "l"], size=10, bold_first=True)
section("1.5", "Scope of the Project")
P("The scope of the work is set by what can be run, under identical conditions, on one laptop:")
bullets(["Languages: Hindi (pivot), English (control pivot), and the targets Marathi, Odia and Kannada.",
         "Model: whisper-base (74M parameters) adapted with LoRA; larger Whisper models are outside the scope.",
         "Data: 45 hours per pivot and 15 hours per target from IndicVoices and LibriSpeech; evaluation on 600-clip samples of "
         "FLEURS (test) and Kathbath (valid).",
         "Compute: 25 training and evaluation runs on one Apple M4 machine with 16 GB of memory, one training seed per configuration.",
         "Deployment: fp16 and 4-bit MLX models with an offline web demonstration.",
         "Out of scope: additional pivots (Marathi → Odia, Kannada → Odia), multiple seeds, and the native-speaker error "
         "analysis planned at Review 1, which was not completed."])

# ---------------------------------------------------------------- Chapter 2
chapter(2, "Background")
section("2.1", "Literature Survey")
for i, s_ in enumerate(["Multilingual Speech Representation Learning", "Weakly-Supervised Multilingual ASR",
                        "Adaptation to Languages Unseen During Pre-Training", "Sequential and Multistage Transfer",
                        "Parameter-Efficient Adaptation", "Indic Speech Resources and Systems"], 1):
    sub(f"2.1.{i}", s_)
    paper("Literature Review", s_)
section("2.2", "Previous Methodologies (Year-wise)")
P(f"{ref('tab:yearwise')} lists the reviewed studies in order of publication, with the main finding of each and the limitation "
  "most relevant to the research questions of this project.")
table("tab:yearwise", "Year-wise summary of previous methodologies",
      [["Year", "Study", "Method / model", "Key finding", "Key limitation"]] + [list(r) for r in YEARWISE],
      [1.1, 2.3, 3.6, 3.85, 3.8], ["c", "l", "l", "l", "l"], size=9.5)
section("2.3", "Research Gap")
paper("Identified Gaps and Proposed Direction", "Gaps in the Literature")
section("2.4", "Tools and Techniques")
P(f"{ref('tab:tools')} lists the hardware, libraries and versions used. All of it is free and open, and the whole project ran "
  "on one laptop.")
V = derived["versions"]
table("tab:tools", "Tools and techniques used", [
    ["Area", "Tool", "Version", "Used for"],
    ["Hardware", "Apple MacBook, M4, 16 GB unified memory", "macOS 27", "All training, evaluation and deployment"],
    ["Language", "Python", V["python"], "All project code"],
    ["Deep learning", "PyTorch (MPS backend)", V["torch"], "Training and evaluation on the Apple GPU"],
    ["Models", "Hugging Face Transformers", V["transformers"], "Whisper model, processor and decoding"],
    ["Adaptation", "PEFT", V["peft"], "LoRA adapters"],
    ["Data", "Datasets, pyarrow, pandas", f"{V['datasets']}, {V['pyarrow']}, {V['pandas']}", "Corpus access, Parquet storage, result tables"],
    ["Audio", "soundfile, librosa", f"{V['soundfile']}, {V['librosa']}", "Decoding and resampling audio"],
    ["Metrics", "jiwer, NumPy", f"{V['jiwer']}, {V['numpy']}", "WER/CER and the paired bootstrap"],
    ["Deployment", "MLX, mlx-whisper", f"{V['mlx']}, {V['mlx-whisper']}", "On-device inference (fp16 and 4-bit)"],
    ["Demonstration", "FastAPI; React, TypeScript, Vite", f"{V['fastapi']}; 19, 6, 8", "Local server and web interface"],
    ["Reporting", "matplotlib, LaTeX (IEEEtran)", V["matplotlib"], "Figures and the research paper"],
], [3.0, 4.5, 2.5, 4.65], ["l", "l", "c", "l"], bold_first=True)

# ---------------------------------------------------------------- Chapter 3
FIG = os.path.join(HERE, "figures")
chapter(3, "Methodology")
section("3.1", "Proposed Methodology")
paper("Identified Gaps and Proposed Direction", "Proposed Direction")
paper("Methodology", "Experimental Design")
figure("fig:pipeline", os.path.join(FIG, "fig_pipeline.png"), "The IndicBridge experimental pipeline. Only the first stage differs: "
       "a related (Hindi) pivot, an unrelated (English) pivot of equal size, or none.",
       note="Data budget, optimiser, decoding and scoring are identical in every condition.")
section("3.2", "Target Languages")
P(f"Kannada provides a comparison outside the Indo-Aryan family, while Odia lets us study a language without a dedicated Whisper "
  f"token. {ref('tab:targets')} summarises what each target tests.")
table("tab:targets", "The three target languages and what each one tests", [
    ["Target", "Family", "Script", "Whisper language token"],
    ["Marathi", "Indo-Aryan, like Hindi", "Devanagari, same as Hindi", "Yes"],
    ["Odia", "Indo-Aryan, like Hindi", "Its own (Odia)", "None; a token is borrowed"],
    ["Kannada", "Dravidian", "Its own (Kannada)", "Yes"],
], [2.6, 3.7, 4.0, 4.35], ["l", "l", "l", "l"], bold_first=True,
      notes="If language family drives the gain, the Hindi pivot should help Marathi and Odia more than Kannada.")
section("3.3", "Model and LoRA Adaptation")
paper("Methodology", "Model and Training", 0, 3)
figure("fig:lora", os.path.join(FIG, "fig_lora.png"), "LoRA on one attention projection: the pre-trained weight stays frozen and "
       "only the low-rank matrices A and B are trained",
       note="Only A and B are trained: 1.18M parameters (1.6% of whisper-base). A multistage run continues the pivot's A and B on the target.")
paper("Methodology", "Model and Training", 3, 4)
section("3.4", "Odia and the Borrowed Language Token")
paper("Methodology", "Odia and the Borrowed Language Token")
section("3.5", "Decoding, Normalization and Metrics")
paper("Methodology", "Decoding, Normalization and Metrics")
RATES = {"hindi": 19.0, "marathi": 18.8, "kannada": 26.0, "odia": 43.7}
import math  # noqa: E402
cap = lambda l, s_: min(440, 10 + math.ceil(1.5 * RATES[l] * s_))  # noqa: E731
P(f"{ref('tab:caps')} shows the output limit that Equation 3.2 gives for clips of different lengths, and {ref('tab:metrics')} "
  "summarises every measure used in this report.")
table("tab:caps", "Output-length limit of Equation 3.2 for each language", [
    ["Language", "Fastest token rate r_L (tokens/s)", "5 s clip", "10 s clip", "20 s clip", "30 s clip"]] +
    [[NAME[l], f"{RATES[l]}", str(cap(l, 5)), str(cap(l, 10)), str(cap(l, 20)), str(cap(l, 30))] for l in ["hindi", "marathi", "kannada", "odia"]],
    [2.4, 4.25, 2.0, 2.0, 2.0, 2.0], ["l", "c", "c", "c", "c", "c"], bold_first=True,
    notes="The limit never exceeds 440 new tokens, the most Whisper's 448-token decoder can emit after its prompt.")
table("tab:metrics", "Evaluation measures", [
    ["Measure", "Definition", "Why it is used"],
    ["WER", "Word errors (S + D + I) per reference word, corpus level", "Standard ASR metric; reported raw and after normalization"],
    ["CER", "The same at character level", "Fairer for Indian languages, where agglutination inflates word-level errors"],
    ["Script validity", "Share of output letters in the target script", "Catches output written in the wrong script"],
    ["Transfer gain G", "WER(direct) − WER(pivot → target)", "The primary dependent variable"],
    ["Δ", "G(Hindi) − G(English)", "Isolates the effect of a related pivot"],
    ["Interaction I", "Δ(target 1) − Δ(target 2)", "Tests whether the Hindi advantage depends on the family"],
    ["RTF and size", "Decoding time ÷ audio time; model megabytes", "The deployment trade-off"],
], [2.6, 5.9, 6.15], ["l", "l", "l"], size=10, bold_first=True)
section("3.6", "Statistical Testing")
paper("Methodology", "Statistical Testing")
section("3.7", "System Architecture")
P(f"{ref('fig:arch')} shows the two halves of the system. The research pipeline prepares the data, runs every training job "
  "through a resumable queue, scores each model with the same evaluation code and writes the results files. The deployment path "
  "merges the LoRA adapters into whisper-base, converts them to MLX, and serves them through a local FastAPI server to a web "
  "interface used during the demonstration. Both run on the same laptop without a network connection.")
figure("fig:arch", os.path.join(FIG, "fig_architecture.png"), "System architecture of the research pipeline and the demonstration",
       note="Everything runs on one laptop: the server serves the scored outputs to the bench and runs the MLX models for live transcription.")

# ---------------------------------------------------------------- Chapter 4
chapter(4, "Implementation")
section("4.1", "Datasets")
paper("Methodology", "Data")
figure("fig:dataprep", os.path.join(FIG, "fig_dataprep.png"), "Data preparation, applied identically to every language",
       note="Test sets (FLEURS test, Kathbath valid) are sampled separately and never trained on.")
D = DATA
trrows = [["Language", "Source", "Role", "Hours", "Clips", "Speakers", "Max clips per speaker"]]
for key, lang, src, role in [("train_hindi_45h", "Hindi", "IndicVoices", "Pivot"), ("train_english_45h", "English", "LibriSpeech clean-100", "Control pivot"),
                             ("train_marathi_15h", "Marathi", "IndicVoices", "Target"), ("train_odia_15h", "Odia", "IndicVoices", "Target"),
                             ("train_kannada_15h", "Kannada", "IndicVoices", "Target")]:
    d = D[key]
    trrows.append([lang, src, role, f"{d['hours']:.1f}", f"{d['clips']:,}", f"{d['speakers']:,}", str(d["max_per_speaker"])])
table("tab:train", "Training data", trrows, [2.0, 3.3, 2.3, 1.5, 1.6, 1.8, 2.15], ["l", "l", "l", "c", "c", "c", "c"], size=10, bold_first=True)
REASONS = [("duration", "Outside 2–30 s"), ("tagged", "Annotation tags"), ("label_too_long", "Label > 443 tokens"),
           ("speaker_cap", "Speaker cap"), ("empty_text", "Empty text")]
drows = [["Language"] + [r for _, r in REASONS] + ["Total"]]
for key, lang in [("train_hindi_45h", "Hindi"), ("train_english_45h", "English"), ("train_marathi_15h", "Marathi"),
                  ("train_odia_15h", "Odia"), ("train_kannada_15h", "Kannada")]:
    dr = D[key]["dropped"]
    vals = [dr.get(k) for k, _ in REASONS]
    drows.append([lang] + [f"{v:,}" if v is not None else "–" for v in vals] + [f"{sum(v or 0 for v in vals):,}"])
table("tab:drops", "Clips removed by each filter while sampling", drows, [2.0, 2.2, 2.2, 2.2, 2.0, 1.9, 2.15],
      ["l", "c", "c", "c", "c", "c", "c"], size=10, bold_first=True)
figure("fig:drops", os.path.join(FIG, "fig_drops.png"), "Clips removed by each filter for the Indian languages", width=13.5)
terows = [["Language", "FLEURS test split", "Too long for the decoder", "FLEURS clips used", "Kathbath valid split", "Kathbath clips used"]]
for l in ["hindi", "marathi", "odia", "kannada"]:
    fl, kb = D[f"test_fleurs_{l}"], D[f"test_kathbath_{l}"]
    terows.append([NAME[l], f"{fl['split_clips']:,}", f"{fl['split_too_long_for_decoder']} ({fl['split_too_long_pct']:.1f}%)",
                   f"{fl['clips']}", f"{kb['split_clips']:,}", f"{kb['clips']}"])
table("tab:test", "Test data and references excluded by the decoder limit", terows, [2.2, 2.4, 2.8, 2.4, 2.45, 2.4],
      ["l", "c", "c", "c", "c", "c"], size=10, bold_first=True, notes="Test clips are a fixed, seeded sample and are never used for training.")
section("4.2", "Implementation")
sub("4.2.1", "Code Organisation")
P(f"The project is a single Python repository. {ref('tab:modules')} lists the modules and what each one does.")
table("tab:modules", "Code modules", [
    ["Module", "Responsibility"],
    ["src/data_prep.py", "Seeded sampling of corpus shards, clip and label filters, Parquet output with statistics"],
    ["src/normalize.py", "Shared text normalizer (contract v3.0.0) with a self-test and a checksum"],
    ["src/train_lora.py", "LoRA training on the Apple GPU with checkpoint and resume"],
    ["src/eval_model.py", "Batched greedy decoding with the per-language output limit"],
    ["src/evaluate.py", "WER, CER and script validity under three scoring rules; per-utterance errors"],
    ["src/experiments.py", "Definitions of the 25 runs"],
    ["src/run_queue.py", "Resumable queue: DONE markers, failure records, dependency order"],
    ["src/analysis.py, src/figures.py", "Gains, interaction, paired bootstrap, result tables and figures"],
    ["src/bench.py", "Throughput and memory benchmark used to choose the model and settings"],
    ["deploy/build_models.py", "Merges each adapter into whisper-base and converts it to MLX (fp16 and 4-bit)"],
    ["deploy/bench_deploy.py", "On-device benchmark of size, speed and accuracy"],
    ["demo/server.py, demo/web/", "FastAPI server and the React web interface used for the demonstration"],
], [5.2, 9.45], ["l", "l"], size=10.5)
sub("4.2.2", "Choosing the Model and Settings")
B = json.load(open(os.path.join(ROOT, "config.json")))["bench"]
brows = [["Model", "Batch", "Precision", "Attention", "Gradient checkpointing", "Clips per second", "Memory (GB)"]]
for r in B["train"]:
    brows.append(["whisper-small", str(r["batch"]), r["precision"], "default", "yes" if r["grad_ckpt"] else "no",
                  f"{r['samples_per_sec']:.2f}" if "samples_per_sec" in r else "out of memory", f"{r['mem_gb']:.1f}" if "mem_gb" in r else "–"])
for r in B["whisper_base_attention"]:
    brows.append(["whisper-base", str(r["batch"]), r["precision"], r["attn"], "no", f"{r['clips_per_sec']:.2f}", f"{r['mem_gb']:.1f}"])
P(f"Before any experiment, every candidate setting was benchmarked on the M4 ({ref('tab:bench')} and {ref('fig:bench')}). "
  "whisper-small reached at most 1.35 clips per second, so the full grid would have taken days; whisper-base with eager "
  "attention in fp32 was the fastest setting that fitted in memory, and it was used for every run.")
table("tab:bench", "Measured training throughput and memory on the Apple M4", brows, [2.4, 1.3, 1.6, 1.8, 2.6, 2.5, 2.45],
      ["l", "c", "c", "c", "c", "c", "c"], size=10, bold_first=True, notes="Memory is capped at about 9.5 GB so that an oversized batch fails instead of swapping.")
figure("fig:bench", os.path.join(FIG, "fig_bench.png"), "Training throughput of each benchmarked setting; the setting used is highlighted", width=13.5)
sub("4.2.3", "Training on One Laptop")
paper("Methodology", "Model and Training", 4)
table("tab:fixes", "Problems met during implementation and how they were solved", [
    ["Problem", "Cause", "Fix"],
    ["The Hindi pivot ran out of memory", "Apple's GPU cached a compiled graph for every label length (4.9 GB)", "Pad labels to multiples of 64 (seven shapes); micro-batch 2 × 8, effective batch 16"],
    ["Evaluation at batch 16 ran out of memory", "Eager attention needs more memory than SDPA", "Evaluation batch 4 for every run; zero-shot rows rescored"],
    ["Default decoding broke Odia", "A repetition penalty blocks Odia's repeating byte tokens; a 200-token cap cut sentences", "Plain greedy decoding, no penalties, the per-language limit of Equation 3.2"],
    ["Untrained models looped", "Hallucinated repetition until the length limit", "The same per-language limit; decoding then ran at 0.05–0.07× real time"],
    ["36–59 GB of audio per language", "Too large to download; first-N sampling would pick one district", "Seeded sampling across shards, filters from metadata"],
    ["Common Voice unavailable", "Its Hugging Face entry exposed only a README", "Kathbath valid as the second test set"],
    ["Bootstrap intervals moved between runs", "One shared random stream; results depended on order", "A fixed seed per comparison"],
    ["The MLX model disagreed with PyTorch", "Timestamps on in MLX, off in training; some clips looped", "Timestamps off (Kannada CER 35.6 → 24.4); temperature fallback"],
    ["Library changes broke the pipeline", "New datasets and Transformers versions changed audio decoding and language settings", "Every version pinned"],
], [3.9, 5.0, 5.75], ["l", "l", "l"], size=9.5, bold_first=True)
sub("4.2.4", "Deployment")
paper("Methodology", "Deployment")
section("4.3", "Training Runs")
P(f"{ref('tab:trainlog')} summarises each training run from its log.")
tl = [["Run", "Starts from", "Steps", "First logged loss", "Final loss", "Mean clips per second", "Approx. training time (min)"]]
for run, start in [("P-hindi", "whisper-base"), ("P-english", "whisper-base"), ("D-marathi", "fresh adapter"), ("D-odia", "fresh adapter"),
                   ("D-kannada", "fresh adapter"), ("H-marathi", "Hindi pivot"), ("H-odia", "Hindi pivot"), ("H-kannada", "Hindi pivot"),
                   ("E-marathi", "English pivot"), ("E-odia", "English pivot"), ("E-kannada", "English pivot"),
                   ("T-odia-assamese", "fresh adapter"), ("T-odia-hindi", "fresh adapter")]:
    L = [json.loads(x) for x in open(os.path.join(ROOT, "runs", run, "train_log.jsonl"))]
    sps = [r["samples_per_sec"] for r in L[1:]] or [L[0]["samples_per_sec"]]
    mean = sum(sps) / len(sps)
    steps = L[-1]["step"]
    tl.append([run, start, f"{steps:,}", f"{L[0]['loss']:.2f}", f"{L[-1]['loss']:.2f}", f"{mean:.2f}", f"{steps * 16 / mean / 60:.0f}"])
table("tab:trainlog", "Training runs, from their logs", tl, [2.7, 2.6, 1.3, 2.0, 1.6, 2.2, 2.25], ["l", "l", "c", "c", "c", "c", "c"],
      size=10, bold_first=True, notes="Training time is estimated from the logged throughput at an effective batch of 16 clips.")
P(f"{ref('fig:losspiv')} and {ref('fig:losstgt')} show the training loss of every run. The English pivot starts and ends far lower "
  "than the Hindi pivot because Whisper already knows English; in the target stage the Hindi-pivot runs start lowest.")
figure("fig:losspiv", os.path.join(FIG, "fig_loss_pivots.png"), "Training loss of the two pivots", width=13.0)
figure("fig:losstgt", os.path.join(FIG, "fig_loss_targets.png"), "Training loss of the target stage for each target and method")

# ---------------------------------------------------------------- Chapter 5
chapter(5, "Results")
section("5.1", "Experimental Setup")
P(f"{ref('tab:setup')} lists the settings shared by every run and {ref('tab:runs')} lists the 25 runs.")
setup = [["Setting", "Value"],
         ["Base model", "whisper-base (74M parameters), frozen"],
         ["LoRA", f"r = {CFG_T['lora_r']}, α = 64, dropout 0.05, on the query and value projections; 1.18M trainable (1.6%)"],
         ["Optimiser", f"AdamW, learning rate 10^{{−3}}, {CFG_T['warmup']} warm-up steps, linear decay, gradient clipping 1.0"],
         ["Batch and precision", f"Effective batch {CFG_T['batch_size'] * CFG_T['grad_accum']}, fp32, eager attention, seed {CFG_T['seed']}"],
         ["Steps", f"Pivot {CFG_P['max_steps']:,}; target {CFG_T['max_steps']:,}"],
         ["Clip filters", "2–30 s; at most 50 clips per speaker (English 120); tagged rows removed; labels ≤ 443 tokens"],
         ["Test sets", "FLEURS test and Kathbath valid: 600 seeded clips each (Hindi FLEURS: all 417)"],
         ["Decoding", "Greedy, no repetition penalty, per-language output limit (Equation 3.2), evaluation batch 4"],
         ["Scoring", "Normalizer contract v3.0.0; raw, normalized and Whisper-normalized scores"],
         ["Hardware", "Apple M4, 16 GB unified memory, PyTorch MPS backend"]]
table("tab:setup", "Experimental setup, identical for every run", setup, [4.0, 10.65], ["l", "l"], bold_first=True)
table("tab:runs", "The 25 runs", [
    ["Group", "Runs", "Starts from", "Trained on", "Purpose"],
    ["Zero-shot (6)", "Hindi, Marathi, Kannada; Odia under the Bengali, Assamese and Hindi tokens", "whisper-base", "–", "Baseline; borrowed-token study before training"],
    ["Pivot (2)", "Hindi pivot, English pivot", "whisper-base", "45 h, 2,000 steps", "Related pivot and unrelated control"],
    ["Pivot-only (6)", "Each pivot evaluated on each target", "Pivot model", "–", "What transfers before target training"],
    ["Direct (3)", "Marathi, Odia, Kannada", "Fresh adapter", "15 h, 1,000 steps", "Reference condition"],
    ["Hindi → target (3)", "Marathi, Odia, Kannada", "Hindi pivot adapter", "15 h, 1,000 steps", "Multistage with a related pivot"],
    ["English → target (3)", "Marathi, Odia, Kannada", "English pivot adapter", "15 h, 1,000 steps", "Multistage with an unrelated pivot"],
    ["Odia token (2)", "Direct Odia under the Assamese and Hindi tokens", "Fresh adapter", "15 h, 1,000 steps", "Borrowed-token study after training"],
], [2.7, 4.2, 2.5, 2.3, 2.95], ["l", "l", "l", "l", "l"], size=10, bold_first=True)
section("5.2", "Result Summary Tables")
paper("Results and Insights", "Baseline and the Effect of Fine-Tuning")
figure("fig:script", os.path.join(FIG, "fig_script.png"), "Share of output letters in the right script, before and after training (FLEURS)", width=13.5)
P(f"{ref('tab:main')} gives the error rates of every model on both test sets; the best value for each language, test set and "
  f"metric is in bold. {ref('fig:wer')} compares the three trained methods.")
mrows = [["Language", "Model", "FLEURS WER", "FLEURS CER", "Kathbath WER", "Kathbath CER", "Target script %"]]
blocks = [("hindi", [("Z-hindi", "Zero-shot"), ("P-hindi", "Fine-tuned (pivot, 45 h)")])]
for t_ in TARGETS:
    blocks.append((t_, [("Z-odia-bengali" if t_ == "odia" else f"Z-{t_}", "Zero-shot"), (f"D-{t_}", "Direct"),
                        (f"H-{t_}", f"Hindi → {NAME[t_]}"), (f"E-{t_}", f"English → {NAME[t_]}")]))
for lang, runs in blocks:
    best = {(ts, m): min(M(r, ts, f"{m}_clean") for r, _ in runs) for ts in TS for m in ("WER", "CER")}
    for i, (rid, lab) in enumerate(runs):
        cells = []
        for ts in TS:
            for m in ("WER", "CER"):
                v = M(rid, ts, f"{m}_clean")
                cells.append([(f1(v), {"bold": v == best[(ts, m)]})])
        mrows.append([NAME[lang] if i == 0 else "", lab] + cells + [f"{M(rid, 'fleurs', 'script_valid'):.0f}"])
table("tab:main", "WER and CER (%) of every model after normalization", mrows, [1.9, 3.4, 1.8, 1.8, 1.9, 1.9, 1.95],
      ["l", "l", "c", "c", "c", "c", "c"], size=10, bold_first=True,
      notes="Target script %: share of output letters in the target language's script, on FLEURS.")
figure("fig:wer", os.path.join(FIG, "fig_wer_methods.png"), "WER of the three trained methods for each target (zero-shot omitted: above 100%)")
P(f"{ref('tab:gains')} and {ref('fig:gains')} give the transfer gains in word errors, and {ref('tab:cergains')} the same in "
  f"character errors. {ref('fig:delta')} shows the Hindi-specific gain Δ.")
grows = [["Target", "Test set", "Hindi pivot gain", "English pivot gain", "Δ = Hindi − English"]]
for t_ in TARGETS:
    for i, ts in enumerate(TS):
        cells = []
        for key in ("hindi_pivot_gain", "english_pivot_gain", "hindi_specific"):
            p_, lo, hi, s_ = G(t_, ts, key)
            cells.append([(ci_txt(p_, lo, hi), {"bold": s_})])
        grows.append([NAME[t_] if i == 0 else "", TS[ts]] + cells)
table("tab:gains", "Transfer gains in WER points with 95% paired-bootstrap intervals", grows, [2.2, 2.0, 3.4, 3.5, 3.55],
      ["l", "l", "c", "c", "c"], size=10, bold_first=True,
      notes="Positive means fewer errors than direct training. Bold: the interval excludes zero. 1,000 resamples of the test clips.")
figure("fig:gains", os.path.join(ROOT, "report", "paper", "figures", "fig_gains.png"),
       "Transfer gain over direct fine-tuning (WER points). Dot: measured gain; line: 95% interval.", width=12.5)
crows = [["Target", "Test set", "Hindi pivot gain", "English pivot gain", "Δ = Hindi − English"]]
for t_ in TARGETS:
    for i, ts in enumerate(TS):
        cells = []
        for key in ("hindi_pivot_gain", "english_pivot_gain", "hindi_specific"):
            p_, lo, hi, s_ = G(t_, ts, key, "CER")
            cells.append([(ci_txt(p_, lo, hi), {"bold": s_})])
        crows.append([NAME[t_] if i == 0 else "", TS[ts]] + cells)
table("tab:cergains", "Transfer gains in CER points with 95% paired-bootstrap intervals", crows, [2.2, 2.0, 3.4, 3.5, 3.55],
      ["l", "l", "c", "c", "c"], size=10, bold_first=True, notes="Bold: the interval excludes zero.")
figure("fig:delta", os.path.join(FIG, "fig_delta.png"), "The Hindi-specific gain Δ for each target, with 95% intervals", width=13.0)
irows = [["Comparison", "FLEURS", "Kathbath"]]
for comp, lab in [("marathi - kannada", "Δ(Marathi) − Δ(Kannada)"), ("odia - kannada", "Δ(Odia) − Δ(Kannada)"), ("marathi - odia", "Δ(Marathi) − Δ(Odia)")]:
    cells = []
    for ts in TS:
        r = next(x for x in inter if x["metric"] == "WER" and x["comparison"] == comp and x["test_set"] == ts)
        cells.append([(ci_txt(float(r["points"]), float(r["ci_low"]), float(r["ci_high"])), {"bold": r["significant"] == "True"})])
    irows.append([lab] + cells)
table("tab:inter", "Difference in the Hindi-specific gain between targets (WER points, 95% CI)", irows, [5.4, 4.6, 4.65],
      ["l", "c", "c"], notes="Each language's test set is resampled independently. Bold: the interval excludes zero.")
porows = [["Target", "Model", "WER", "CER", "Target script %"]]
for t_ in TARGETS:
    for i, (rid, lab) in enumerate([("Z-odia-bengali" if t_ == "odia" else f"Z-{t_}", "Untrained"), (f"X-hindi-{t_}", "Hindi pivot only"),
                                    (f"X-english-{t_}", "English pivot only")]):
        porows.append([NAME[t_] if i == 0 else "", lab, f1(M(rid)), f1(M(rid, "fleurs", "CER_clean")), f"{M(rid, 'fleurs', 'script_valid'):.0f}"])
table("tab:pivotonly", "Pivot models scored on the targets before any target training (FLEURS)", porows, [2.6, 4.0, 2.4, 2.4, 3.25],
      ["l", "l", "c", "c", "c"], size=10, bold_first=True)
figure("fig:pivotonly", os.path.join(FIG, "fig_pivot_only.png"), "CER of the pivot models on each target before target training", width=13.5)
table("tab:pivots", "How much each pivot stage changed the model", [
    ["Pivot", "Data", "First logged loss", "Final loss", "LoRA update norm"],
    ["Hindi", "IndicVoices, 45 h", f"{float(pivots['P-hindi']['first_loss']):.2f}", f"{float(pivots['P-hindi']['last_loss']):.2f}", f"{float(pivots['P-hindi']['lora_update_norm']):.1f}"],
    ["English", "LibriSpeech, 45 h", f"{float(pivots['P-english']['first_loss']):.2f}", f"{float(pivots['P-english']['last_loss']):.2f}", f"{float(pivots['P-english']['lora_update_norm']):.1f}"],
], [2.4, 3.6, 3.0, 2.6, 3.05], ["l", "l", "c", "c", "c"], bold_first=True,
      notes="Update norm: Frobenius norm of the learned low-rank weight updates. The English stage moved the model less.")
frows = [["Language", "Whisper tokens per letter", "Whisper tokens per word", "FLEURS references too long for the decoder"]]
for l in ["hindi", "marathi", "kannada", "odia"]:
    frows.append([NAME[l], fert[l]["tokens_per_char"], fert[l]["tokens_per_word"], f"{D[f'test_fleurs_{l}']['split_too_long_pct']:.1f}%"])
table("tab:fert", "Tokenizer cost and the decoder limit (FLEURS references)", frows, [3.0, 3.6, 3.6, 4.45], ["l", "c", "c", "c"], bold_first=True)
figure("fig:fert", os.path.join(FIG, "fig_fertility.png"), "Whisper tokens per letter for each language (FLEURS references)", width=10.5)
P("The Odia sentence “ଏହା ମାରିଆ ତଳେ ପତଳା ଓ ଉଚ୍ଚଭୁମି ତଳେ ଅଧିକ ମୋଟା ହୋଇଥାଏ।” from the FLEURS test set shows why: "
  f"{ref('fig:bytes')} lists the tokens Whisper's tokenizer produces for it.", align=WD_ALIGN_PARAGRAPH.LEFT)
TOK = json.load(open(os.path.join(ROOT, "report", "slides", "tokens_cache.json")))
figure("fig:bytes", os.path.join(FIG, "fig_odia_bytes.png"), "Whisper's tokens for one Odia test sentence: almost every token is a single byte",
       note=f"{len(TOK['tokens'])} tokens for {TOK['letters']} letters ({TOK['per_letter']:.2f} per letter). Grey: one UTF-8 byte, "
            "shown in hexadecimal; outlined: a space.")
td = derived["token_diff"]
orows = [["Borrowed token", "Zero-shot WER (FLEURS / Kathbath)", "Odia script, before → after", "Trained WER (FLEURS / Kathbath)", "Difference from Bengali, FLEURS"]]
for code, nm, z, run in [("bn", "Bengali", "Z-odia-bengali", "D-odia"), ("as", "Assamese", "Z-odia-assamese", "T-odia-assamese"), ("hi", "Hindi", "Z-odia-hindi", "T-odia-hindi")]:
    diff = "reference" if code == "bn" else ci_txt(*td[f"{run}|fleurs"])
    orows.append([f"<|{code}|> {nm}", f"{f1(M(z))} / {f1(M(z, 'kathbath'))}", f"{M(z, 'fleurs', 'script_valid'):.0f}% → {M(run, 'fleurs', 'script_valid'):.0f}%",
                  f"{f1(M(run))} / {f1(M(run, 'kathbath'))}", diff])
table("tab:odia", "The borrowed language token for Odia", orows, [2.7, 3.2, 2.7, 3.1, 2.95], ["l", "c", "c", "c", "c"], size=10, bold_first=True,
      notes="Difference: WER points saved relative to the Bengali token, 95% paired-bootstrap interval; no interval excludes zero.")
figure("fig:odiatok", os.path.join(FIG, "fig_odia_tokens.png"), "Odia WER after training under each borrowed token", width=12.5)
nrows = [["Target", "Test set", "Raw WER", "Normalized WER (ours)", "Whisper normalizer WER", "Method order changes"]]
for t_ in TARGETS:
    methods = ["Z-odia-bengali" if t_ == "odia" else f"Z-{t_}", f"D-{t_}", f"H-{t_}", f"E-{t_}"]
    for i, ts in enumerate(TS):
        order = {c: tuple(sorted(methods, key=lambda x: M(x, ts, c))) for c in ("WER_raw", "WER_clean", "WER_whisper_norm")}
        ch = [n for n, c in (("raw", "WER_raw"), ("Whisper", "WER_whisper_norm")) if order[c] != order["WER_clean"]]
        nrows.append([NAME[t_] if i == 0 else "", TS[ts], f1(M(f"H-{t_}", ts, "WER_raw")), f1(M(f"H-{t_}", ts)),
                      f1(M(f"H-{t_}", ts, "WER_whisper_norm")), ", ".join(ch) if ch else "No"])
table("tab:norm", "The Hindi-pivot models under three scoring rules", nrows, [2.0, 2.0, 2.0, 3.0, 3.0, 2.65], ["l", "l", "c", "c", "c", "c"],
      size=10, bold_first=True)
figure("fig:norm", os.path.join(FIG, "fig_norm.png"), "WER of the Hindi-pivot models under the three scoring rules")
dpl = {(r["run_id"], r["precision"]): r for r in deploy}
drows = [["Model", "Weights", "Size (MB)", "RTF", "WER", "CER", "PyTorch WER, same clips"]]
for rid, lab in [("P-hindi", "Hindi pivot"), ("H-marathi", "Hindi → Marathi"), ("H-odia", "Hindi → Odia"), ("H-kannada", "Hindi → Kannada")]:
    for i, pr in enumerate(("fp16", "q4")):
        r = dpl[(rid, pr)]
        drows.append([lab if i == 0 else "", "fp16" if pr == "fp16" else "4-bit", f"{float(r['model_mb']):.0f}", f"{float(r['rtf']):.3f}",
                      f1(r["WER"]), f1(r["CER"]), f1(r["WER_pytorch_same_clips"]) if i == 0 else ""])
table("tab:deploy", "On-device deployment with MLX on the Apple M4 (100 FLEURS clips per model)", drows, [3.3, 1.7, 1.8, 1.6, 1.6, 1.6, 3.05],
      ["l", "c", "c", "c", "c", "c", "c"], size=10, bold_first=True, notes="RTF: decoding time divided by audio duration.")
figure("fig:deploy", os.path.join(FIG, "fig_deploy.png"), "Accuracy of the fp16 and 4-bit MLX models against PyTorch on the same clips")
section("5.3", "Analysis of Results")
for i, (s_, t_) in enumerate([("Relatedness or Data Quantity?", "Relatedness or Data Quantity"),
                              ("Indo-Aryan Versus Dravidian Targets", "Indo-Aryan Versus Dravidian Targets"),
                              ("Odia: Tokenizer Cost and the Borrowed Language Token", "Odia: Tokenizer Cost and the Borrowed Token"),
                              ("Effect of the Scoring Rules", "Effect of the Scoring Rules"),
                              ("On-Device Deployment", "On-Device Deployment")], 1):
    sub(f"5.3.{i}", t_)
    paper("Results and Insights", s_)
sub("5.3.6", "Limitations")
paper("Results and Insights", "Limitations")
section("5.4", "Comparison with Existing Methods")
gm = {t_: (G(t_, "fleurs", "hindi_pivot_gain")[0], G(t_, "kathbath", "hindi_pivot_gain")[0]) for t_ in TARGETS}
P(f"{ref('tab:compare')} places the multistage gains measured here next to the study this project builds on. The absolute error "
  "rates are not comparable, because the languages, model sizes and test sets differ; the size and direction of the gain over "
  "direct fine-tuning are. The reference study reports one related pivot; this project adds the unrelated control, which is the "
  "part that tests the relatedness explanation.")
table("tab:compare", "Comparison with existing methods (gain of multistage over direct fine-tuning)", [
    ["Study", "Pivot → target", "Model", "Target data", "Gain over direct (WER points)"],
    ["Pillai et al. (2026)", "Tamil → Malasar", "Whisper small / medium", "≈4.6 h", "4.5"],
    ["This project", "Hindi → Marathi", "whisper-base + LoRA", "15 h", f"{sg(gm['marathi'][0])} / {sg(gm['marathi'][1])}"],
    ["This project", "Hindi → Odia", "whisper-base + LoRA", "15 h", f"{sg(gm['odia'][0])} / {sg(gm['odia'][1])}"],
    ["This project", "Hindi → Kannada", "whisper-base + LoRA", "15 h", f"{sg(gm['kannada'][0])} / {sg(gm['kannada'][1])}"],
    ["This project", "English → each target", "whisper-base + LoRA", "15 h", "No significant positive gain"],
    ["Bhogale et al. (2023)", "Joint training, 12 languages", "IndicWhisper", "10.7K h", "Not reported (no pivot stage)"],
], [3.3, 3.2, 3.0, 2.0, 3.15], ["l", "l", "l", "c", "c"], size=10, bold_first=True, notes="This project: FLEURS / Kathbath.")

# ---------------------------------------------------------------- Chapter 6
chapter(6, "Inferences")
section("6.1", "Key Findings")
z_scr = [M("Z-odia-bengali" if l == "odia" else f"Z-{l}", "fleurs", "script_valid") for l in ["hindi", "marathi", "kannada", "odia"]]
gk = G("kannada", "fleurs", "english_pivot_gain")
dk = (G("kannada", "fleurs", "hindi_specific")[0], G("kannada", "kathbath", "hindi_specific")[0])
ix = next(x for x in inter if x["metric"] == "WER" and x["comparison"] == "marathi - kannada" and x["test_set"] == "kathbath")
rtf = [float(r["rtf"]) for r in deploy if r["precision"] == "fp16"]
bullets([
    f"Fine-tuning is essential. Untrained whisper-base exceeds 100% WER for all four languages and writes between "
    f"{min(z_scr):.0f}% and {max(z_scr):.0f}% of its letters in the right script; every trained model writes 100%.",
    f"The gain is not explained by data quantity. The English pivot, with the same 45 hours and 2,000 steps, gives no significant "
    f"positive gain for any target and makes Kannada worse on FLEURS ({sg(gk[0])}). The Hindi pivot improves all three targets: "
    f"Marathi {sg(gm['marathi'][0])} / {sg(gm['marathi'][1])}, Odia {sg(gm['odia'][0])} / {sg(gm['odia'][1])}, Kannada "
    f"{sg(gm['kannada'][0])} / {sg(gm['kannada'][1])} WER points (FLEURS / Kathbath).",
    f"Relatedness helps, but not only within the family. Hindi beats English for Dravidian Kannada as well ({sg(dk[0])} / {sg(dk[1])}). "
    f"A larger Indo-Aryan effect appears once, Marathi against Kannada on Kathbath ({sg(float(ix['points']))}), and Marathi also "
    f"shares Hindi's script.",
    f"For Odia, the borrowed token stops mattering after training (all three within about one WER point, no reliable difference). "
    f"The tokenizer is the real ceiling: {fert['odia']['tokens_per_char']} tokens per Odia letter, and "
    f"{D['test_fleurs_odia']['split_too_long_pct']:.1f}% of FLEURS references are too long to decode at all.",
    "Scoring choices change the numbers. Whisper's own normalizer deletes Indic vowel signs, roughly halves WER, and changes the "
    "ranking of methods in two of six cases.",
    f"The fp16 MLX models run {1 / max(rtf):.0f}–{1 / min(rtf):.0f} times faster than real time on the laptop, within 2.5 WER points of "
    f"PyTorch; 4-bit quantization breaks Kannada (CER {f1(dpl[('H-kannada', 'fp16')]['CER'])} → {f1(dpl[('H-kannada', 'q4')]['CER'])}).",
], numbered=True)
section("6.2", "Interpretation of Results")
P(f"{ref('tab:answers')} gives the answer to each research question and the table that supports it.")
table("tab:answers", "Research questions and the answers this project gives", [
    ["Question", "Answer", "Evidence"],
    ["Relatedness or data quantity?", "Not data quantity: the related pivot helps, the equal unrelated pivot does not", ref("tab:gains")],
    ["RQ1: Indo-Aryan or Dravidian?", "Not established: Hindi helps all three; a larger Indo-Aryan effect appears only for Marathi on Kathbath", ref("tab:inter")],
    ["RQ2: which token for Odia?", "Any of the three after training; none differs reliably", ref("tab:odia")],
    ["RQ3: do scoring rules matter?", "Yes: Whisper's normalizer halves WER and can reorder methods", ref("tab:norm")],
], [4.0, 7.8, 2.85], ["l", "l", "l"], size=10, bold_first=True)
section("6.3", "Implications of the Study")
P("For research, the project gives a controlled test of the explanation usually offered for multistage transfer, and a scoring "
  "protocol for Indic scripts that keeps vowel signs. Both can be reused by other low-resource speech projects.")
P("For industry, it shows that recognition for Indian languages can run fully offline on a consumer laptop, which matters where "
  "connectivity is poor or audio is private. The results also give practical guidance: choose a pivot that shares sounds with the "
  "target rather than the largest available corpus, and for languages such as Odia invest in the tokenizer, because the language "
  "token is not the bottleneck.")

section("6.4", "Fulfilment of Objectives")
dmin = min(((t_, ts) + G(t_, ts, "hindi_specific") for t_ in TARGETS for ts in TS), key=lambda x: x[2])
ix_all = {(x["test_set"], x["comparison"]): x for x in inter if x["metric"] == "WER"}
ixt = lambda ts, c: ci_txt(float(ix_all[(ts, c)]["points"]), float(ix_all[(ts, c)]["ci_low"]), float(ix_all[(ts, c)]["ci_high"]))
pt_gap = max(abs(float(r["WER"]) - float(r["WER_pytorch_same_clips"])) for r in deploy if r["precision"] == "fp16")
P(f"{ref('tab:objectives')} checks each objective against the statistical test that decides it. A difference is counted as "
  "reliable only when its paired-bootstrap 95% confidence interval (1,000 resamples) excludes zero.")
table("tab:objectives", "Fulfilment of objectives, with the statistical evidence", [
    ["Objective", "Status", "Statistical evidence"],
    ["Relatedness against data quantity", "Achieved",
     f"Δ = G(Hindi) − G(English) is positive for all 6 target and test-set pairs and every 95% CI excludes zero; smallest: "
     f"{NAME[dmin[0]]}, {TS[dmin[1]]} {ci_txt(*dmin[2:5])} ({ref('tab:gains')})"],
    ["Indo-Aryan against Dravidian (RQ1)", "Achieved; answer is mixed",
     f"FLEURS: all three between-target differences include zero. Kathbath: Marathi − Kannada {ixt('kathbath', 'marathi - kannada')} "
     f"and Marathi − Odia {ixt('kathbath', 'marathi - odia')} exclude zero ({ref('tab:inter')})"],
    ["Borrowed token for Odia (RQ2)", "Achieved",
     f"Trained WER relative to Bengali: Assamese {ci_txt(*td['T-odia-assamese|fleurs'])}, Hindi {ci_txt(*td['T-odia-hindi|fleurs'])} "
     f"(FLEURS); both intervals include zero ({ref('tab:odia')})"],
    ["Effect of scoring rules (RQ3)", "Achieved",
     f"Marathi FLEURS WER {f1(M('H-marathi'))} with our normalizer against {f1(M('H-marathi', 'fleurs', 'WER_whisper_norm'))} with "
     f"Whisper's; method order changes in 2 of 6 comparisons ({ref('tab:norm')})"],
    ["Offline deployment", "Achieved",
     f"fp16 RTF {min(rtf):.3f}–{max(rtf):.3f}; WER within {pt_gap:.1f} points of PyTorch on the same 100 clips ({ref('tab:deploy')})"],
    ["Native-speaker error analysis (Review 1 plan)", "Not completed", "Annotation sheets prepared but not filled in time; no test run"],
    ["Additional pivots for Odia (Review 1 plan)", "Not done", f"Moved to future work ({ref('tab:future')})"],
], [3.9, 2.6, 8.15], ["l", "l", "l"], size=10, bold_first=True)

# ---------------------------------------------------------------- Chapter 7
chapter(7, "Impression Report")
section("7.1", "Personal Learning Experience")
LEARN = [
    ("Gourab Dash", "training pipeline and Odia",
     "Gourab built the training pipeline: LoRA adapters on whisper-base with PEFT, training on the Apple M4 GPU through PyTorch MPS, "
     f"and the resumable queue that ran all 25 runs. He benchmarked whisper-small against whisper-base to choose the model and settings "
     f"({ref('tab:bench')}) and solved the out-of-memory errors of the Hindi pivot by padding labels to multiples of 64 and changing "
     "the micro-batch layout. He also implemented the Odia experiments: the borrowed-token study with the Bengali, Assamese and "
     f"Hindi tokens, the tokenizer-cost measurement and the per-language decoder limit (Equation 3.2). The work involved GPU memory "
     "management on Apple silicon, designing ablations that are fixed before any result is seen, and handling a script that Whisper "
     "encodes almost byte by byte."),
    ("Divyansh Mahecha", "Hindi",
     "Divyansh was responsible for Hindi, the related pivot of the study. This covered the 45-hour "
     "IndicVoices pivot data and its checks, the gate test that the pivot had to pass before the target runs "
     f"(Hindi FLEURS WER {f1(M('Z-hindi'))} → {f1(M('P-hindi'))}, Kathbath {f1(M('Z-hindi', 'kathbath'))} → {f1(M('P-hindi', 'kathbath'))}), "
     "and the pivot-only evaluations that show what the Hindi pivot transfers before any target training. The work involved "
     "preparing a large spontaneous-speech corpus, reading error rates above 100%, and separating acoustic transfer from "
     "script transfer."),
    ("Parth Nandkumar Khandagale", "Marathi",
     "Parth was responsible for Marathi, the Indo-Aryan target that shares Hindi's Devanagari script. This covered the 15-hour "
     "Marathi training data and the direct, Hindi-pivot and English-pivot Marathi results on FLEURS and Kathbath, where the "
     f"Hindi pivot gave its largest gains ({sg(gm['marathi'][0])} and {sg(gm['marathi'][1])} WER points). He also examined the "
     f"pivot-only result, in which the Hindi pivot already wrote Marathi in Devanagari and lowered CER from {f1(M('Z-marathi', 'fleurs', 'CER_clean'))} "
     f"to {f1(M('X-hindi-marathi', 'fleurs', 'CER_clean'))}. The work involved comparing methods with paired confidence intervals and "
     "recognising that a shared script and a shared language family cannot be separated with Marathi alone."),
    ("Kaushal BC", "Kannada",
     "Kaushal was responsible for Kannada, the Dravidian target that tests whether the Hindi gain is limited to Indo-Aryan "
     "languages. This covered the 15-hour Kannada training data, the Kannada results on both test sets, where Hindi still "
     f"helped ({sg(gm['kannada'][0])} and {sg(gm['kannada'][1])} WER points) while the English pivot made FLEURS WER worse "
     f"({sg(G('kannada', 'fleurs', 'english_pivot_gain')[0])}), and the deployment finding that 4-bit quantization breaks Kannada "
     f"(CER {f1(dpl[('H-kannada', 'fp16')]['CER'])} → {f1(dpl[('H-kannada', 'q4')]['CER'])}). The work involved reading results "
     "that do not follow the expected family pattern and checking how model compression affects one language more than others."),
]
for n, area, text in LEARN:
    mixed([(f"{n} ({area}): ", {"bold": True}), (text, {})])
section("7.2", "Skill Enhancement")
P(f"{ref('tab:skills')} lists the skills the project required and where in this report each one appears.")
table("tab:skills", "Skills exercised in the project", [
    ["Area", "What the project required", "Where"],
    ["Speech recognition", "Fine-tuning Whisper; controlling decoding; language tokens", "Chapters 3 and 4"],
    ["Parameter-efficient learning", "LoRA with PEFT; continuing an adapter across stages", "Section 3.3"],
    ["Experimental design", "Matched controls; choices fixed before results (the Bengali token)", "Section 3.1"],
    ["Statistics", "Paired bootstrap intervals; comparing gains between targets", "Section 3.6"],
    ["Data engineering", "Sampling 36–59 GB corpora; filtering; Parquet", "Section 4.1"],
    ["Systems", "Benchmarking; memory debugging on Apple GPUs; a resumable job queue", "Section 4.2"],
    ["Deployment", "MLX conversion; quantization trade-offs", "Sections 4.2.4 and 5.3.5"],
    ["Web development", "FastAPI server; React interface", "Appendix 3"],
    ["Research communication", "IEEE paper; presentation; this report", "–"],
], [3.8, 7.6, 3.25], ["l", "l", "l"], size=10.5, bold_first=True)
# ---------------------------------------------------------------- Chapter 8
chapter(8, "Conclusion and Future Work")
section("8.1", "Conclusion")
paper("Conclusion and Future Scope", None, 0, 1)
section("8.2", "Future Work")
paper("Conclusion and Future Scope", None, 1)
P(f"{ref('tab:future')} lists each next step and what it would test.")
table("tab:future", "Future work and what each step would test", [
    ["Direction", "What it would test"],
    ["A Dravidian pivot (Tamil or Telugu)", "Whether family matching helps when the target is Dravidian"],
    ["Marathi → Odia and Kannada → Odia pivots", "Whether a closer relative, or a different family, changes the Odia gain"],
    ["Several training seeds", "Whether the gains hold across training runs, not only across test samples"],
    ["whisper-small and larger models", "Whether the pattern survives at higher accuracy"],
    ["A target that separates script from family", "Whether Marathi's extra gain comes from the shared Devanagari script"],
    ["A tokenizer with Odia pieces", "Whether removing the decoder-length ceiling changes Odia accuracy"],
    ["Native-speaker error analysis", "Which kinds of errors the Hindi pivot corrects"],
], [6.2, 8.45], ["l", "l"], size=10.5, bold_first=True)

# ---------------------------------------------------------------- References (APA 7)
h = heading("REFERENCES", 1)
plan.append((1, "REFERENCES", "refs"))
REFS = [
    "Ardila, R., Branson, M., Davis, K., Kohler, M., Meyer, J., Henretty, M., Morais, R., Saunders, L., Tyers, F. M., & Weber, G. (2020). Common Voice: A massively-multilingual speech corpus. In *Proceedings of the Twelfth Language Resources and Evaluation Conference* (pp. 4218–4222). European Language Resources Association.",
    "Babu, A., Wang, C., Tjandra, A., Lakhotia, K., Xu, Q., Goyal, N., Singh, K., von Platen, P., Saraf, Y., Pino, J., Baevski, A., Conneau, A., & Auli, M. (2022). XLS-R: Self-supervised cross-lingual speech representation learning at scale. In *Proceedings of Interspeech 2022* (pp. 2278–2282). https://doi.org/10.21437/Interspeech.2022-143",
    "Bhogale, K., Sundaresan, S., Raman, A., Javed, T., Khapra, M. M., & Kumar, P. (2023). Vistaar: Diverse benchmarks and training sets for Indian language ASR. In *Proceedings of Interspeech 2023* (pp. 4384–4388). https://doi.org/10.21437/Interspeech.2023-2589",
    "Bisani, M., & Ney, H. (2004). Bootstrap estimates for confidence intervals in ASR performance evaluation. In *Proceedings of the 2004 IEEE International Conference on Acoustics, Speech, and Signal Processing* (Vol. 1, pp. I-409–I-412). https://doi.org/10.1109/ICASSP.2004.1326009",
    "Conneau, A., Baevski, A., Collobert, R., Mohamed, A., & Auli, M. (2021). Unsupervised cross-lingual representation learning for speech recognition. In *Proceedings of Interspeech 2021* (pp. 2426–2430). https://doi.org/10.21437/Interspeech.2021-329",
    "Conneau, A., Ma, M., Khanuja, S., Zhang, Y., Axelrod, V., Dalmia, S., Riesa, J., Rivera, C., & Bapna, A. (2023). FLEURS: Few-shot learning evaluation of universal representations of speech. In *2022 IEEE Spoken Language Technology Workshop (SLT)* (pp. 798–805). https://doi.org/10.1109/SLT54892.2023.10023141",
    "Ferraz, T. P., Zanon Boito, M., Brun, C., & Nikoulina, V. (2024). Multilingual DistilWhisper: Efficient distillation of multi-task speech models via language-specific experts. In *Proceedings of the 2024 IEEE International Conference on Acoustics, Speech and Signal Processing* (pp. 10716–10720). https://doi.org/10.1109/ICASSP48485.2024.10447520",
    "Hannun, A., Digani, J., Katharopoulos, A., & Collobert, R. (2023). *MLX: Efficient and flexible machine learning on Apple silicon* [Computer software]. https://github.com/ml-explore/mlx",
    "Houlsby, N., Giurgiu, A., Jastrzebski, S., Morrone, B., de Laroussilhe, Q., Gesmundo, A., Attariyan, M., & Gelly, S. (2019). Parameter-efficient transfer learning for NLP. In *Proceedings of the 36th International Conference on Machine Learning* (pp. 2790–2799). PMLR.",
    "Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large language models. In *International Conference on Learning Representations*.",
    "Javed, T., Bhogale, K., Raman, A., Kumar, P., Kunchukuttan, A., & Khapra, M. M. (2023). IndicSUPERB: A speech processing universal performance benchmark for Indian languages. *Proceedings of the AAAI Conference on Artificial Intelligence, 37*(11), 12942–12950. https://doi.org/10.1609/aaai.v37i11.26521",
    "Javed, T., Nawale, J., George, E., Joshi, S., Bhogale, K., Mehendale, D., Sethi, I., Ananthanarayanan, A., Faquih, H., Palit, P., Ravishankar, S., Sukumaran, S., Panchagnula, T., Murali, S., Gandhi, K., R, A., M, M., Vaijayanthi, C., Karunganni, K., . . . Khapra, M. (2024). IndicVoices: Towards building an inclusive multilingual speech dataset for Indian languages. In *Findings of the Association for Computational Linguistics: ACL 2024* (pp. 10740–10782). https://doi.org/10.18653/v1/2024.findings-acl.639",
    "Mangrulkar, S., Gugger, S., Debut, L., Belkada, Y., Paul, S., Bossan, B., & Tietz, M. (2022). *PEFT: State-of-the-art parameter-efficient fine-tuning methods* [Computer software]. https://github.com/huggingface/peft",
    "Panayotov, V., Chen, G., Povey, D., & Khudanpur, S. (2015). Librispeech: An ASR corpus based on public domain audio books. In *Proceedings of the 2015 IEEE International Conference on Acoustics, Speech and Signal Processing* (pp. 5206–5210). https://doi.org/10.1109/ICASSP.2015.7178964",
    "Pfeiffer, J., Vulić, I., Gurevych, I., & Ruder, S. (2020). MAD-X: An adapter-based framework for multi-task cross-lingual transfer. In *Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing* (pp. 7654–7673). https://doi.org/10.18653/v1/2020.emnlp-main.617",
    "Pillai, L. G., Manohar, K., Raju, B. K., & Sherly, E. (2026). Multistage fine-tuning strategies for automatic speech recognition in low-resource languages. *ACM Transactions on Asian and Low-Resource Language Information Processing, 25*(8), 1–12. https://doi.org/10.1145/3813800",
    "Piñeiro-Martín, A., García-Mateo, C., Docío-Fernández, L., López-Pérez, M. del C., & Rehm, G. (2024). Weighted cross-entropy for low-resource languages in multilingual speech recognition. In *Proceedings of Interspeech 2024* (pp. 1235–1239). https://doi.org/10.21437/Interspeech.2024-734",
    "Pratap, V., Tjandra, A., Shi, B., Tomasello, P., Babu, A., Kundu, S., Elkahky, A., Ni, Z., Vyas, A., Fazel-Zarandi, M., Baevski, A., Adi, Y., Zhang, X., Hsu, W.-N., Conneau, A., & Auli, M. (2024). Scaling speech technology to 1,000+ languages. *Journal of Machine Learning Research, 25*(97), 1–52.",
    "Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2023). Robust speech recognition via large-scale weak supervision. In *Proceedings of the 40th International Conference on Machine Learning* (pp. 28492–28518). PMLR.",
    "Rouditchenko, A., Khurana, S., Thomas, S., Feris, R., Karlinsky, L., Kuehne, H., Harwath, D., Kingsbury, B., & Glass, J. (2023). Comparison of multilingual self-supervised and weakly-supervised speech pre-training for adaptation to unseen languages. In *Proceedings of Interspeech 2023* (pp. 2268–2272). https://doi.org/10.21437/Interspeech.2023-1061",
    "Song, Z., Zhuo, J., Yang, Y., Ma, Z., Zhang, S., & Chen, X. (2024). LoRA-Whisper: Parameter-efficient and extensible multilingual ASR. In *Proceedings of Interspeech 2024* (pp. 3934–3938). https://doi.org/10.21437/Interspeech.2024-892",
    "Wolf, T., Debut, L., Sanh, V., Chaumond, J., Delangue, C., Moi, A., Cistac, P., Rault, T., Louf, R., Funtowicz, M., Davison, J., Shleifer, S., von Platen, P., Ma, C., Jernite, Y., Plu, J., Xu, C., Le Scao, T., Gugger, S., . . . Rush, A. (2020). Transformers: State-of-the-art natural language processing. In *Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing: System Demonstrations* (pp. 38–45). https://doi.org/10.18653/v1/2020.emnlp-demos.6",
    "Xu, T., Huang, K., Guo, P., Zhou, Y., Huang, L., Xue, H., & Xie, L. (2024). Towards rehearsal-free multilingual ASR: A LoRA-based case study on Whisper. In *Proceedings of Interspeech 2024* (pp. 2534–2538). https://doi.org/10.21437/Interspeech.2024-1953",
]
for entry in REFS:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.left_indent, pf.first_line_indent = Cm(1.27), Cm(-1.27)
    pf.space_after, pf.line_spacing = Pt(8), 1.15
    for i, part in enumerate(entry.split("*")):
        if part:
            runs_into(p, part, 12, italic=bool(i % 2))

# ---------------------------------------------------------------- Appendix
CH[0] = "A"
heading("APPENDICES", 1)
plan.append((1, "APPENDICES", "app"))
heading("APPENDIX 1: REPRODUCING THE EXPERIMENTS", 2)
plan.append((2, "APPENDIX 1: REPRODUCING THE EXPERIMENTS", "app:1"))
P(f"All commands run from the repository root on the Apple M4 machine. {ref('tab:commands')} lists them in order.")
table("tab:commands", "Commands to reproduce the experiments", [
    ["Step", "Command"],
    ["Check the normalizer", "python src/normalize.py --checksum"],
    ["Benchmark settings", "python src/bench.py"],
    ["Prepare data", "python src/data_prep.py"],
    ["Run all 25 experiments", "python src/run_queue.py"],
    ["Tables and confidence intervals", "PYTHONPATH=src python src/analysis.py"],
    ["Figures", "PYTHONPATH=src python src/figures.py"],
    ["Build MLX models", "python deploy/build_models.py"],
    ["Deployment benchmark", "python deploy/bench_deploy.py"],
    ["Start the demonstration", "python demo/server.py  (then open http://127.0.0.1:8000)"],
], [4.3, 10.35], ["l", "l"], size=10.5, bold_first=True)
heading("APPENDIX 2: THE NORMALIZATION CONTRACT", 2)
plan.append((2, "APPENDIX 2: THE NORMALIZATION CONTRACT", "app:2"))
P("Every score in this report uses the same normalizer (src/normalize.py, contract version 3.0.0). It applies these steps in order:")
bullets(["Unicode NFC normalization, so that the same visible letter has one encoding.",
         "Removal of annotation tags such as [noise], <unk> and {…}.",
         "Mapping of Devanagari, Odia, Bengali and Kannada digits to Western digits.",
         "Removal of punctuation, including the danda (।) and double danda (॥).",
         "Collapsing of whitespace.",
         "Vowel signs (matras), the virama and the anusvara are kept; a self-test checks this on every run."], numbered=True)
table("tab:normex", "One Hindi phrase under the two normalizers", [
    ["Normalizer", "Output"],
    ["Input", "नमस्ते आप कैसे हैं"],
    ["Our normalizer (contract v3.0.0)", "नमस्ते आप कैसे हैं"],
    ["Whisper's BasicTextNormalizer", "नमस त आप क स ह"],
], [5.0, 9.65], ["l", "l"], size=11, bold_first=True, indic_cols=(1,),
      notes="Whisper's normalizer replaces every vowel sign with a space, which splits words into fragments.")
heading("APPENDIX 3: THE DEMONSTRATION APPLICATION", 2)
plan.append((2, "APPENDIX 3: THE DEMONSTRATION APPLICATION", "app:3"))
P("The demonstration runs on the laptop with the network switched off. A test clip or a live recording is transcribed by the MLX "
  "models; the bench shows any test clip written by every model with its errors marked against the reference.")
figure("fig:demo", os.path.join(ROOT, ".impeccable", "review", "r3", "d-hero-clip.png"), "The demonstration application: a test clip transcribed by every model")
figure("fig:bench2", os.path.join(ROOT, ".impeccable", "review", "r2", "d-bench.png"), "The bench: any test clip, every model, errors marked")
heading("APPENDIX 4: SAMPLE TRANSCRIPTS", 2)
plan.append((2, "APPENDIX 4: SAMPLE TRANSCRIPTS", "app:4"))
P(f"{ref('tab:samples')} shows real outputs from the FLEURS test set.")
table("tab:samples", "Sample transcripts from the test sets", [
    ["Model", "Output"],
    ["Hindi reference", "यह खोज पक्षियों में पंखों के विकास की पूरी जानकारी भी प्रदान करती है."],
    ["Zero-shot whisper-base", "Yer koj pakshio me panko ke vikaz ki pudi jaankari vi pradhan karti hai."],
    ["Hindi pivot (45 h)", "यह खोज़ पक्षियो में पंखों के विकास की पूरी जानकारी भी प्रदान करती है"],
    ["Kannada reference", "ಸಹ ಕುಸ್ತಿಪಟುಗಳು ಸಹ ಲೂನಾ ಅವರಿಗೆ ಗೌರವ ಸಲ್ಲಿಸಿದರು."],
    ["Hindi pivot, no Kannada training", "सहाकुस्ती पटुगलु सहा लूना वरेगे दौरवा सलीसी दरू"],
], [4.6, 10.05], ["l", "l"], size=11, bold_first=True, indic_cols=(1,),
      notes="The Hindi pivot writes Kannada speech phonetically in Devanagari: the sounds transfer, the script does not.")
heading("APPENDIX 5: PROJECT SCHEDULE AND TEAM CONTRIBUTIONS", 2)
plan.append((2, "APPENDIX 5: PROJECT SCHEDULE AND TEAM CONTRIBUTIONS", "app:5"))
P(f"{ref('fig:gantt')} shows the project schedule, from the Review 1 design in August to the experiments, deployment and "
  "write-up in the first week of November.")
figure("fig:gantt", os.path.join(HERE, "figures", "fig_gantt.png"), "Project schedule (Gantt chart)")
P(f"{ref('tab:contrib')} lists the part of the project each member owned.")
table("tab:contrib", "Team contributions", [
    ["Member", "Area", "Work"],
    ["Gourab Dash", "Training pipeline; Odia", "LoRA training on the M4, model and settings benchmark, run queue for all 25 runs including both pivots; Odia borrowed-token study, tokenizer cost and decoder limit"],
    ["Divyansh Mahecha", "Hindi", "Hindi pivot data (IndicVoices, 45 h), pivot gate test, pivot-only evaluations"],
    ["Parth Nandkumar Khandagale", "Marathi", "Marathi target data (15 h), Marathi results and analysis, pivot-only script result"],
    ["Kaushal BC", "Kannada", "Kannada target data (15 h), Kannada results and analysis, 4-bit deployment check for Kannada"],
    [[red("[Confirm owner]")], "Deployment and demo", "MLX conversion, on-device benchmark, offline demonstration application"],
    ["All members", "Presentation", "Introduction: Parth; explanation of the method: Gourab; results and conclusion: Divyansh and Kaushal"],
], [3.6, 3.4, 7.65], ["l", "l", "l"], size=10.5, bold_first=True)


# ======================================================================= save
zoom = doc.settings.element.find(qn("w:zoom"))
if zoom is not None and zoom.get(qn("w:percent")) is None:
    zoom.set(qn("w:percent"), "100")
json.dump(plan, open(os.path.join(HERE, "toc_plan.json"), "w"), indent=0)
json.dump({"labels": labels, "figs": fig_list, "tabs": tab_list}, open(os.path.join(HERE, "captions.json"), "w"), indent=0, ensure_ascii=False)
doc.save(OUT)
print(f"wrote {OUT}: {len(plan)} contents entries, {len(fig_list)} figures, {len(tab_list)} tables")
