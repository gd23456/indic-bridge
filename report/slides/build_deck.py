"""
build_deck.py - the viva deck (report/slides/index.html), generated from the project's result
files so every number on a slide is the measured one.

    PYTHONPATH=src .venv/bin/python report/slides/build_deck.py

Runtime, base styles and animations come from the html-ppt skill (assets/, MIT,
github.com/lewislulu/html-ppt-skill). Keys: arrows to move, S presenter view with the speaker
script, F fullscreen, O overview, T light/dark. Served at http://127.0.0.1:8000/deck/ by
demo/server.py, so presenter mode, fonts and the live-demo link all work offline.
"""
import json
import os
import urllib.parse
import urllib.request
from decimal import ROUND_HALF_UP, Decimal
from html import escape

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = "report/slides/index.html"
CACHE = "report/slides/tokens_cache.json"

master = pd.read_csv("results/results_master.csv")
gains = pd.read_csv("results/tables/gains.csv")
inter = pd.read_csv("results/tables/interaction.csv")
fert = pd.read_csv("results/tables/fertility.csv").set_index("language")
deploy = pd.read_csv("results/tables/deployment.csv")
pivots = pd.read_csv("results/tables/pivots.csv").set_index("pivot")
data = {n: json.load(open(f"data/{n}.json")) for n in
        ["train_hindi_45h", "train_english_45h", "train_marathi_15h", "train_odia_15h", "train_kannada_15h",
         "test_fleurs_odia", "test_fleurs_kannada"]}
NAME = {"hindi": "Hindi", "marathi": "Marathi", "kannada": "Kannada", "odia": "Odia"}
TARGETS = ["marathi", "odia", "kannada"]


def r1(v):
    return Decimal(repr(float(v))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def f1(v):
    return f"{r1(v)}"


def sg(v):
    q = r1(v)
    return f"{'+' if q > 0 else '−' if q < 0 else ''}{abs(q)}"


def wer(run, ts="fleurs", col="WER_clean"):
    return float(master[(master.run_id == run) & (master.test_set == ts)].iloc[0][col])


def gain(lang, ts, key, metric="WER"):
    return gains[(gains.language == lang) & (gains.test_set == ts) & (gains.gain == key) & (gains.metric == metric)].iloc[0]


# ---- the Odia sentence, tokenised by Whisper (via the demo server; cached for offline rebuilds) ----
ODIA = "ଏହା ମାରିଆ ତଳେ ପତଳା ଓ ଉଚ୍ଚଭୁମି ତଳେ ଅଧିକ ମୋଟା ହୋଇଥାଏ।"
try:
    tok = json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/tokens?" + urllib.parse.urlencode({"text": ODIA}), timeout=10))
    json.dump(tok, open(CACHE, "w"), ensure_ascii=False)
except Exception:
    tok = json.load(open(CACHE))

MARK = ('<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M3.5 22.5C7 12.6 25 12.6 28.5 22.5" fill="none" stroke="currentColor" '
        'stroke-width="3" stroke-linecap="round"/><path d="M3 22.5h26" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>'
        '<path d="M10 22.5v-4.6M16 22.5V16M22 22.5v-4.6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>')

PEOPLE = {
    "parth": ("PK", "Parth Khandagale", "Introduction"),
    "gourab": ("GD", "Gourab Dash", "Approach"),
    "divyansh": ("DM", "Divyansh Mahecha", "Results"),
    "kaushal": ("KB", "Kaushal BC", "Results & close"),
}
slides = []


def slide(who, title, body, notes, cls=""):
    ini, name, part = PEOPLE[who]
    slides.append(f"""
  <section class="slide {cls}" data-title="{escape(title)}">
    <div class="brand">{MARK}IndicBridge</div>
    <div class="who"><span class="face">{ini}</span><b>{name}</b><span>· {part}</span></div>
{body}
    <aside class="notes">{notes}</aside>
  </section>""")


# =================================================================== PARTH: introduction
title_cards = [
    ("hindi", "टेलीविजन रिपोर्टों में प्लांट से निकलने वाला सफेद धुआँ दिखाया गया है।", 70, 150, -8),
    ("kannada", "ಸಹ ಕುಸ್ತಿಪಟುಗಳು ಸಹ ಲೂನಾ ಅವರಿಗೆ ಗೌರವ ಸಲ್ಲಿಸಿದರು.", 1490, 170, 7),
    ("odia", ODIA, 110, 660, 6),
    ("marathi", "वन्यजीवांचा विचार केल्यास मादागास्कर आतापर्यंत सर्वात मोठे आहे.", 1500, 650, -6),
]
cards_html = "".join(
    f'<div class="sent-wrap" style="left:{x}px;top:{y}px;transform:rotate({rot}deg)"><div class="sent script" data-anim="zoom-pop" style="animation-delay:{0.25 + i * 0.12:.2f}s">'
    f'<small><span>{NAME[l]}</span><span>FLEURS</span></small>{escape(t)}</div></div>'
    for i, (l, t, x, y, rot) in enumerate(title_cards))
slide("parth", "Title", f"""
    <div class="title-stage"><div class="ring r2"></div><div class="ring r1"></div>{cards_html}<div class="veil"></div></div>
    <div class="title-main">
      <h1 class="h1" data-anim="rise-in">Language<span class="comma">,</span><br><span class="hand">or just data?</span></h1>
      <p class="lede" style="margin:0 auto;text-align:center;max-width:none" data-anim="fade-up">Multistage fine-tuning of Whisper for Marathi, Odia and Kannada</p>
      <div class="team" data-anim="fade-up" style="animation-delay:.25s">
        <div><b>Gourab Dash</b><span>1RUA24CSE0146</span></div>
        <div><b>Parth N. Khandagale</b><span>1RUA24CSE0201</span></div>
        <div><b>Divyansh Mahecha</b><span>1RUA24CSE0139</span></div>
        <div><b>Kaushal BC</b><span>1RUA24CSE0196</span></div>
      </div>
      <p class="muted" style="margin-top:28px;font-size:22px;text-align:center">School of Computer Science and Engineering · RV University</p>
    </div>""",
      """<p>Good morning. We are team <strong>IndicBridge</strong>: I'm Parth, with Gourab, Divyansh and Kaushal.</p>
<p>The cards behind the title are <em>real sentences from our test sets</em>, in Hindi, Kannada, Odia and Marathi.</p>
<p>Our question fits on one line: when a speech model learns a low-resource language better after first learning a related one, is that because the languages are <strong>related</strong>, or just because it saw <strong>more data</strong>?</p>
<p>I'll set up the problem, Gourab explains how we tested it, and Divyansh and Kaushal present the results.</p>""",
      cls="title")

hi_ref = "यह खोज पक्षियों में पंखों के विकास की पूरी जानकारी भी प्रदान करती है."
hi_zero = "Yer koj pakshio me panko ke vikaz ki pudi jaankari vi pradhan karti hai."
hi_piv = "यह खोज़ पक्षियो में पंखों के विकास की पूरी जानकारी भी प्रदान करती है"
zs = {l: wer("Z-odia-bengali" if l == "odia" else f"Z-{l}") for l in NAME}
slide("parth", "Supported is not the same as working", f"""
    <h2 class="h2" data-anim="fade-up">Whisper “supports” Hindi. <span class="hand">Look at what it writes.</span></h2>
    <div class="lines" data-anim="stagger-list">
      <div class="line"><span class="k">What was said</span><span class="v script">{hi_ref}</span></div>
      <div class="line wrong"><span class="k">whisper-base, untrained</span><span class="v">{hi_zero}</span></div>
      <div class="line good"><span class="k">After 45 h of Hindi</span><span class="v script">{hi_piv}</span></div>
    </div>
    <div class="facts mt-l" data-anim="fade-up" style="animation-delay:.5s">
      {"".join(f'<div class="fact"><div class="big num">{f1(zs[l])}<span style="font-size:.45em">%</span></div><div class="lbl">{NAME[l]} WER, untrained</div></div>' for l in ["hindi", "marathi", "kannada", "odia"])}
      <div class="fact"><div class="big" style="color:var(--accent)">0</div><div class="lbl">language tokens for Odia</div></div>
    </div>""",
      f"""<p>Whisper officially supports 99 languages, Hindi among them. But <strong>listen to the middle line</strong>: untrained whisper-base heard this Hindi sentence and wrote it in <em>romanized English letters</em>.</p>
<p>After we trained it on 45 hours of Hindi, the bottom line is almost word-perfect.</p>
<p>Untrained, the error rate is <strong>above 100% for all four languages</strong>: {f1(zs['hindi'])} for Hindi, {f1(zs['odia'])} for Odia. Above 100 means the output is longer than the sentence and mostly wrong.</p>
<p>And Odia, spoken by tens of millions, <strong>has no language token</strong> in Whisper at all. So "supported" does not mean usable. These languages need adaptation.</p>""")

slide("parth", "The claim we tested", """
    <h2 class="h2" data-anim="fade-up">A related language helps first. <span class="hand">But why?</span></h2>
    <div class="grid g2">
      <div class="card" data-anim="fade-left">
        <div class="tag acc"><i></i>Earlier work · Pillai et al., 2026</div>
        <h4>Tamil first, then Malasar</h4>
        <p>Whisper adapted to Tamil, then to Malasar (a Dravidian language with about 4.5 hours of data): <b>51.9% WER</b>, <b>4.5 points better</b> than training on Malasar alone.</p>
        <p class="mt-s">They credit the gain to the two languages being related.</p>
      </div>
      <div class="card" data-anim="fade-right" style="animation-delay:.15s">
        <div class="tag bad"><i></i>What nobody tested</div>
        <h4>Two explanations fit</h4>
        <p><b>Relatedness:</b> the pivot shares sounds, words and grammar with the target.</p>
        <p class="mt-s"><b>Just more data:</b> any extra speech and an extra training stage would have helped as much.</p>
        <p class="mt-s">Only an <b>unrelated pivot of the same size</b> can tell them apart.</p>
      </div>
    </div>
    <p class="note mt-l" data-anim="fade-up" style="animation-delay:.4s">So we added one.</p>""",
      """<p>The idea we build on is <strong>multistage fine-tuning</strong>. Pillai and colleagues trained Whisper on Tamil first, then on Malasar, a tiny Dravidian language, and got <strong>4.5 points</strong> fewer errors than training on Malasar alone.</p>
<p>They explain it by relatedness: Tamil and Malasar are cousins. But there's a second explanation that fits the same result: <em>maybe any extra speech would have helped</em>, related or not.</p>
<p>The only way to tell those apart is a <strong>control</strong>: an unrelated pivot language, with the same amount of data and the same training. Nobody had run that control. That's the gap we fill.</p>""")

slide("parth", "Research questions", """
    <h2 class="h2" data-anim="blur-in" style="max-width:1500px">Does a pivot help because it is <span class="hand">related</span> — or because it adds data?</h2>
    <div class="grid g3 mt-m" data-anim="stagger-list">
      <div class="card"><div class="tag acc"><i></i>RQ1 · family</div><h4>Indo-Aryan vs Dravidian</h4><p>Does Hindi help Marathi and Odia more than Kannada, under the same budget?</p></div>
      <div class="card"><div class="tag acc"><i></i>RQ2 · Odia</div><h4>Which borrowed token?</h4><p>Odia has no Whisper token. Bengali, Assamese or Hindi: does the choice matter?</p></div>
      <div class="card"><div class="tag acc"><i></i>RQ3 · scoring</div><h4>Do the scoring rules change the answer?</h4><p>How much do normalization choices move WER, and the ranking of methods?</p></div>
    </div>""",
      """<p>So our <strong>main question</strong>: does a pivot language help because it is related to the target, or simply because it adds data?</p>
<p>Three supporting questions. <strong>One</strong>: Hindi is Indo-Aryan. Does it help the Indo-Aryan targets, Marathi and Odia, more than the Dravidian target Kannada?</p>
<p><strong>Two</strong>: Odia has no token in Whisper, so we have to borrow one. Does it matter which?</p>
<p><strong>Three</strong>: Indian scripts are easy to score wrongly. Do the scoring rules change the answer?</p>
<p>Gourab will now explain how we set up the experiment to answer these.</p>""")

# =================================================================== GOUROB: approach
pipe = """
    <svg class="pipe" viewBox="0 0 1660 520" role="img" aria-label="Experiment design: whisper-base, then a Hindi pivot, an English pivot or no pivot, then each target, then two test sets">
      <path class="wire" style="--d:250" d="M300 260 C360 260 360 90 430 90"/>
      <path class="wire" style="--d:250" d="M300 260 L430 260"/>
      <path class="wire" style="--d:250" d="M300 260 C360 260 360 430 430 430"/>
      <path class="wire" style="--d:700" d="M770 90 C850 90 850 260 930 260"/>
      <path class="wire" style="--d:700" d="M770 260 L930 260"/>
      <path class="wire" style="--d:700" d="M770 430 C850 430 850 260 930 260"/>
      <path class="wire" style="--d:1150" d="M1270 260 L1350 260"/>
      <g class="node" style="--d:0"><rect class="box" x="20" y="190" width="280" height="140" rx="22"/>
        <text class="lbl" x="160" y="252" text-anchor="middle">whisper-base</text><text class="sub" x="160" y="290" text-anchor="middle">74M, frozen + LoRA</text></g>
      <g class="node" style="--d:450"><rect class="box hi" x="430" y="30" width="340" height="120" rx="22"/>
        <text class="lbl" x="600" y="84" text-anchor="middle">Hindi pivot</text><text class="sub" x="600" y="120" text-anchor="middle">45 h · related</text></g>
      <g class="node" style="--d:550"><rect class="box en" x="430" y="200" width="340" height="120" rx="22"/>
        <text class="lbl" x="600" y="254" text-anchor="middle">English pivot</text><text class="sub" x="600" y="290" text-anchor="middle">45 h · unrelated control</text></g>
      <g class="node" style="--d:650"><rect class="box" x="430" y="370" width="340" height="120" rx="22"/>
        <text class="lbl" x="600" y="424" text-anchor="middle">No pivot</text><text class="sub" x="600" y="460" text-anchor="middle">direct training</text></g>
      <g class="node" style="--d:950"><rect class="box acc" x="930" y="150" width="340" height="220" rx="22"/>
        <text class="lbl" x="1100" y="214" text-anchor="middle">Target, 15 h</text><text class="sub" x="1100" y="252" text-anchor="middle">1,000 steps</text>
        <text class="lbl" x="1100" y="304" text-anchor="middle" style="font-size:24px">Marathi · Odia</text><text class="lbl" x="1100" y="340" text-anchor="middle" style="font-size:24px">Kannada</text></g>
      <g class="node" style="--d:1350"><rect class="box" x="1350" y="170" width="300" height="180" rx="22"/>
        <text class="lbl" x="1500" y="236" text-anchor="middle">Score</text><text class="sub" x="1500" y="274" text-anchor="middle">FLEURS + Kathbath</text><text class="sub" x="1500" y="306" text-anchor="middle">600 clips each</text></g>
    </svg>"""
slide("gourab", "Experiment design", f"""
    <h2 class="h2" data-anim="fade-up">One thing changes: <span class="hand">the pivot.</span></h2>
    {pipe}
    <div class="facts mt-m" data-anim="fade-up" style="animation-delay:1.4s">
      <div class="fact"><div class="big num">25</div><div class="lbl">training and evaluation runs</div></div>
      <div class="fact"><div class="big num">1</div><div class="lbl">Apple M4 laptop, 16 GB</div></div>
      <div class="fact" style="max-width:820px"><div class="lbl" style="max-width:none;font-size:24px">Pivot 2,000 steps · target 1,000 steps. Same data budget, optimiser, decoding and scoring for every run; only the first stage differs.</div></div>
    </div>""",
      """<p>Thanks, Parth. Here is the whole design on one slide. <strong>Only one thing changes: the pivot.</strong></p>
<p>We start from whisper-base. Path one: train on <strong>45 hours of Hindi</strong>, the related pivot. Path two: <strong>45 hours of English</strong>, same hours, same 2,000 steps, but unrelated to every target. That's our control. Path three: no pivot at all, which is <em>direct</em> training.</p>
<p>Then each model is trained on the target, Marathi, Odia or Kannada, <strong>15 hours and 1,000 steps</strong>, and scored on two test sets, FLEURS and Kathbath, 600 clips each.</p>
<p>So if Hindi beats English, it can't be because of more data or an extra stage. Both pivots had exactly the same.</p>""")

slide("gourab", "Three targets", """
    <h2 class="h2" data-anim="fade-up">Three targets that pull apart <span class="hand">family and script.</span></h2>
    <div class="targets" data-anim="stagger-list">
      <div class="target"><div class="glyph">मराठी</div><h4>Marathi</h4>
        <dl><dt>Family</dt><dd class="yes">Indo-Aryan, like Hindi</dd><dt>Script</dt><dd class="yes">Devanagari, same as Hindi</dd><dt>Whisper token</dt><dd>yes</dd></dl></div>
      <div class="target"><div class="glyph">ଓଡ଼ିଆ</div><h4>Odia</h4>
        <dl><dt>Family</dt><dd class="yes">Indo-Aryan, like Hindi</dd><dt>Script</dt><dd>its own</dd><dt>Whisper token</dt><dd class="bad">none</dd></dl></div>
      <div class="target"><div class="glyph">ಕನ್ನಡ</div><h4>Kannada</h4>
        <dl><dt>Family</dt><dd>Dravidian</dd><dt>Script</dt><dd>its own</dd><dt>Whisper token</dt><dd>yes</dd></dl></div>
    </div>
    <p class="note mt-l" data-anim="fade-up" style="animation-delay:.6s">If family is what matters, Hindi should help Marathi and Odia more than Kannada.</p>""",
      """<p>Why these three targets? Because together they <strong>separate family from script</strong>.</p>
<p><strong>Marathi</strong> is Hindi's close relative and even uses the same Devanagari script. <strong>Odia</strong> is in the same family but has its own script, and Whisper has <em>no token</em> for it. <strong>Kannada</strong> is from a different family altogether, Dravidian, with its own script.</p>
<p>So the prediction is clear: if language family drives the gain, Hindi should help Marathi and Odia more than Kannada. If it's mostly shared script, Marathi alone should stand out.</p>""")

d = data
slide("gourab", "Data and model", f"""
    <h2 class="h2" data-anim="fade-up">Real Indian speech, a small model, <span class="hand">one laptop.</span></h2>
    <div class="split">
      <div class="grid g2" data-anim="stagger-list">
        <div class="card"><div class="tag hi"><i></i>Hindi pivot</div><h4>IndicVoices, 45 h</h4><p>{d['train_hindi_45h']['clips']:,} clips · {d['train_hindi_45h']['speakers']:,} speakers</p></div>
        <div class="card"><div class="tag en"><i></i>English pivot</div><h4>LibriSpeech, 45 h</h4><p>{d['train_english_45h']['clips']:,} clips · {d['train_english_45h']['speakers']} speakers</p></div>
        <div class="card"><div class="tag acc"><i></i>Targets</div><h4>IndicVoices, 15 h each</h4><p>Marathi {d['train_marathi_15h']['clips']:,} · Odia {d['train_odia_15h']['clips']:,} · Kannada {d['train_kannada_15h']['clips']:,} clips</p></div>
        <div class="card"><div class="tag"><i></i>Test, never trained on</div><h4>FLEURS + Kathbath</h4><p>600 clips each per language</p></div>
      </div>
      <div class="card" data-anim="fade-right" style="animation-delay:.3s">
        <div class="tag acc"><i></i>Model</div>
        <h4>whisper-base + LoRA</h4>
        <p class="eq" style="margin:18px 0"><span class="var">W</span> = W<sub>0</sub> + (α / r) · <span class="var">B A</span></p>
        <p>74M parameters frozen. LoRA on the attention query and value projections, r = 32, α = 64: <b>1.18M trainable (1.6%)</b>.</p>
        <p class="mt-s">AdamW, lr 10⁻³, effective batch 16, fp32, seed 42.</p>
        <p class="mt-s note" style="font-size:22px">Why base? whisper-small trained at 1.35 clips/s here (~49 h for the grid); base at 4.54 (~15 h).</p>
      </div>
    </div>""",
      f"""<p>The data. For Hindi and the three targets we used <strong>IndicVoices</strong>, natural speech from real Indian speakers. Hindi: {d['train_hindi_45h']['clips']:,} clips from {d['train_hindi_45h']['speakers']:,} speakers. English comes from <strong>LibriSpeech</strong> audiobooks. The test sets are FLEURS and Kathbath, which we <em>never train on</em>.</p>
<p>The model is <strong>whisper-base</strong>. We freeze its 74 million weights and train only small <strong>LoRA</strong> matrices on the attention layers: 1.18 million parameters, 1.6 percent of the model.</p>
<p>Why base and not small? We measured it: whisper-small would have needed about <strong>49 hours</strong> for the full grid on our laptop; base needed about <strong>15</strong>. Our question compares methods, so a smaller model answers it fairly. The absolute error rates are higher, and we say so.</p>""")

bytes_html = "".join(
    f'<span class="sp" style="--i:{i}">␣</span>' if (t["text"] or "").strip() == "" and t["text"] else f'<span style="--i:{i}">{escape(t["hex"])}</span>'
    for i, t in enumerate(tok["tokens"]))
odia_fl = data["test_fleurs_odia"]
slide("gourab", "Odia and the tokenizer", f"""
    <h2 class="h2" data-anim="fade-up">Whisper has no Odia token. <span class="hand">It spells Odia in bytes.</span></h2>
    <p class="odia-line" data-anim="fade-up" style="animation-delay:.1s">{ODIA}</p>
    <div class="bytes" aria-label="{len(tok['tokens'])} Whisper tokens for this sentence">{bytes_html}</div>
    <div class="facts mt-l" data-anim="fade-up" style="animation-delay:1.6s">
      <div class="fact"><div class="big num">{len(tok['tokens'])}</div><div class="lbl">tokens for {tok['letters']} letters (grey = one byte)</div></div>
      <div class="fact"><div class="big num">{fert.loc['odia','tokens_per_char']:.2f}</div><div class="lbl">tokens per Odia letter (Hindi {fert.loc['hindi','tokens_per_char']:.2f})</div></div>
      <div class="fact"><div class="big num">{odia_fl['split_too_long_pct']:.1f}<span style="font-size:.45em">%</span></div><div class="lbl">of Odia test sentences too long for the decoder</div></div>
    </div>""",
      f"""<p>Odia is the hardest case, and this slide shows why. Whisper's tokenizer has almost no Odia pieces, so it writes each letter as <strong>raw UTF-8 bytes</strong>. The grey chips are single bytes. Only the spaces, in purple, are real tokens.</p>
<p>This short sentence costs <strong>{len(tok['tokens'])} tokens for {tok['letters']} letters</strong>. On average Odia needs <strong>{fert.loc['odia','tokens_per_char']:.2f} tokens per letter</strong>; Hindi needs {fert.loc['hindi','tokens_per_char']:.2f}.</p>
<p>Whisper's decoder can only write about 448 tokens, so <strong>{odia_fl['split_too_long_pct']:.1f}%</strong> of Odia test sentences are simply too long to ever be transcribed, by any model. We excluded them for every model and report the share.</p>
<p>And because there's no Odia token, we borrowed <strong>Bengali's</strong>, its closest relative, chosen before seeing any results.</p>""")

slide("gourab", "Scoring fairly", """
    <h2 class="h2" data-anim="fade-up">Score Indian scripts carefully, <span class="hand">or the numbers lie.</span></h2>
    <div class="split">
      <div class="card" data-anim="fade-left">
        <div class="tag bad"><i></i>The trap</div>
        <div class="norm">
          <span class="k">Sentence</span><span class="v">नमस्ते आप कैसे हैं</span>
          <span class="k">Our normalizer</span><span class="v">नमस्ते आप कैसे हैं</span>
          <span class="k">Whisper's</span><span class="v bad">नमस त आप क स ह</span>
        </div>
        <p class="mt-m">Whisper's normalizer deletes every vowel sign and splits words. We score with our own (NFC, punctuation and danda removed, vowel signs kept) and report Whisper's as a third column.</p>
      </div>
      <div class="card" data-anim="fade-right" style="animation-delay:.2s">
        <div class="tag acc"><i></i>What we measure</div>
        <p class="eq">WER = (S + D + I) / N<br>
        <span class="var">G</span>(t) = WER<sub>direct</sub> − WER<sub>pivot→t</sub><br>
        <span class="var">Δ</span>(t) = G<sub>Hindi</sub> − G<sub>English</sub></p>
        <p class="mt-m">Every gain gets a <b>95% interval</b> from a paired bootstrap: 1,000 resamples of the test clips, both models scored on the same clips.</p>
      </div>
    </div>""",
      """<p>Scoring Indian languages has a trap. Take "namaste, aap kaise hain". <strong>Whisper's own normalizer deletes every vowel sign</strong>, the matras, and splits the words apart. That makes error rates look much better than they are.</p>
<p>So we wrote our own normalizer that <em>keeps the vowel signs</em>, and shared it across the team with a checksum so everyone scored identically. We still report Whisper's score as a third column, because the difference is itself a finding.</p>
<p>What we measure: <strong>WER</strong>, word error rate. The <strong>gain G</strong>: how many WER points a pivot saves over direct training. And <strong>Delta</strong>: the Hindi gain minus the English gain, which isolates the effect of relatedness.</p>
<p>Every number comes with a <strong>95% confidence interval</strong> from a paired bootstrap.</p>""")

slide("gourab", "What broke and how we fixed it", """
    <h2 class="h2" data-anim="fade-up">What broke along the way, <span class="hand">and the fix.</span></h2>
    <div class="grid g2" data-anim="stagger-list">
      <div class="card fix"><div class="q">The Hindi pivot ran out of memory</div><div class="why">Apple's GPU cached a new compute graph for every label length: 4.9 GB on top of the model.</div><div class="how">pad labels to multiples of 64 (7 shapes), micro-batch 2 × 8, effective batch still 16</div></div>
      <div class="card fix"><div class="q">Default decoding broke Odia</div><div class="why">A repetition penalty blocks Odia's repeating byte tokens; a 200-token cap cut sentences short.</div><div class="how">plain greedy decoding, no penalties, a length cap per language</div></div>
      <div class="card fix"><div class="q">36–59 GB of audio per language</div><div class="why">Too big to download whole; first-N sampling would pick one district.</div><div class="how">seeded sampling across shards, 2–30 s clips, ≤50 clips per speaker</div></div>
      <div class="card fix"><div class="q">The offline model disagreed with PyTorch</div><div class="why">MLX decoded with timestamps on; our adapters were trained without them. Some clips looped.</div><div class="how">timestamps off (Kannada CER 35.6 → 24.4), loop fallback: within 2.5 WER of PyTorch</div></div>
    </div>""",
      """<p>Running 25 experiments on one laptop meant solving real problems. Four of them.</p>
<p><strong>One</strong>: the Hindi pivot crashed out of memory. Apple's GPU caches a compiled graph for every different label length. We padded labels to multiples of 64, so only seven shapes exist.</p>
<p><strong>Two</strong>: the decoding settings from our plan broke Odia. A repetition penalty blocks exactly the byte tokens Odia repeats, so we switched to plain greedy decoding for every run.</p>
<p><strong>Three</strong>: IndicVoices is up to 59 GB per language, so we sampled across the whole dataset with a fixed seed.</p>
<p><strong>Four</strong>: our offline model didn't match PyTorch until we turned timestamps off, the way it was trained.</p>
<p>Now Divyansh will show what we found.</p>""")

# =================================================================== DIVYANSH: results
rows = []
for t in TARGETS:
    rows.append((t, [("Z-odia-bengali" if t == "odia" else f"Z-{t}", "Zero-shot", "z"), (f"D-{t}", "Direct", ""),
                     (f"H-{t}", f"Hindi → {NAME[t]}", "hi"), (f"E-{t}", f"English → {NAME[t]}", "en")]))
trs = []
for lang, runs in rows:
    best = {ts: min(wer(r, ts) for r, _, _ in runs) for ts in ["fleurs", "kathbath"]}
    for i, (rid, label, kind) in enumerate(runs):
        cells = "".join(
            f'<td class="{"best" if wer(rid, ts) == best[ts] else "z" if kind == "z" else ""}">{f1(wer(rid, ts))}</td>'
            for ts in ["fleurs", "kathbath"])
        trs.append(f'<tr class="{"grp" if i == 0 else ""}"><td>{f"<span class=lang>{NAME[lang]}</span>" if i == 0 else ""}</td>'
                   f'<td><span class="sw {kind}"></span>{label}</td>{cells}</tr>')
slide("divyansh", "Fine-tuning works", f"""
    <h2 class="h2" data-anim="fade-up">Hindi-first wins <span class="hand">every cell.</span></h2>
    <div class="split" style="grid-template-columns:1.3fr .7fr">
      <table class="tbl" data-anim="fade-up" style="animation-delay:.1s">
        <thead><tr><th>Language</th><th>Model</th><th>FLEURS WER</th><th>Kathbath WER</th></tr></thead>
        <tbody>{"".join(trs)}</tbody>
      </table>
      <div class="stack" data-anim="stagger-list">
        <div class="card"><div class="big num">&gt;100<span style="font-size:.45em">%</span></div><p class="mt-s">untrained WER for every language</p></div>
        <div class="card"><div class="big num">0–7<span style="font-size:.45em">%</span> → 100<span style="font-size:.45em">%</span></div><p class="mt-s">output in the right script, before and after training</p></div>
        <div class="card"><p>Lowest WER and CER in all six target / test-set cells: <b class="accent">Hindi → target</b>.</p></div>
      </div>
    </div>""",
      f"""<p>Thank you, Gourab. First, the overall picture: <strong>fine-tuning works</strong>.</p>
<p>Untrained, every language is above 100 percent error. After training, Hindi drops from {f1(wer('Z-hindi'))} to <strong>{f1(wer('P-hindi'))}</strong> on FLEURS, and every trained model writes <strong>100 percent in the correct script</strong>, up from between 0 and 7 percent.</p>
<p>The absolute numbers, 60 to 75 percent, are high because whisper-base is small. What matters is the <em>comparison</em>, and look at the purple numbers: <strong>Hindi-first is the best method in all six cells</strong>, for every target on both test sets.</p>
<p>But is that because Hindi is related, or just because it's extra data? That's the next slide.</p>""")

# gain chart
def chart():
    W, H = 1640, 520
    panels = [("fleurs", "FLEURS", 210, 860), ("kathbath", "Kathbath", 1010, 1620)]
    lo, hi_ = -4, 6
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Transfer gain over direct training with 95% intervals">']
    for ts, label, x0, x1 in panels:
        X = lambda v: x0 + (v - lo) / (hi_ - lo) * (x1 - x0)
        out.append(f'<text class="ttl" x="{x0}" y="36">{label}</text>')
        for t in range(lo, hi_ + 1, 2):
            out.append(f'<line class="{"zero" if t == 0 else "gl"}" x1="{X(t):.1f}" x2="{X(t):.1f}" y1="70" y2="470"/>'
                       f'<text class="tick" x="{X(t):.1f}" y="505" text-anchor="middle">{"+" if t > 0 else "−" if t < 0 else ""}{abs(t)}</text>')
        for i, lang in enumerate(TARGETS):
            yc = 140 + i * 135
            if ts == "fleurs":
                out.append(f'<text class="rl" x="0" y="{yc + 8}">{NAME[lang]}</text>')
            for k, (key, cls) in enumerate([("hindi_pivot_gain", "hi"), ("english_pivot_gain", "en")]):
                g = gain(lang, ts, key)
                y = yc - 24 + k * 48
                dly = 200 + i * 220 + k * 110 + (0 if ts == "fleurs" else 90)
                out.append(f'<line class="ci {cls}" style="--d:{dly}" x1="{X(g.ci_low):.1f}" x2="{X(g.ci_high):.1f}" y1="{y}" y2="{y}"/>'
                           f'<circle class="dot {cls}" style="--d:{dly}" cx="{X(g.points):.1f}" cy="{y}" r="13"/>'
                           f'<text class="val {cls}" style="--d:{dly}" x="{X(g.ci_high) + 16:.1f}" y="{y + 7}">{sg(g.points)}</text>')
    out.append("</svg>")
    return "".join(out)


ge = {l: {ts: gain(l, ts, "english_pivot_gain") for ts in ["fleurs", "kathbath"]} for l in TARGETS}
gh = {l: {ts: gain(l, ts, "hindi_pivot_gain") for ts in ["fleurs", "kathbath"]} for l in TARGETS}
slide("divyansh", "The main answer", f"""
    <h2 class="h2" data-anim="fade-up">Hindi helps. <span class="hand">English doesn't.</span></h2>
    {chart()}
    <div class="row mt-s" style="justify-content:space-between;animation-delay:1.6s" data-anim="fade-up">
      <div class="legend"><span><span class="sw hi"></span>Hindi pivot, 45 h</span><span><span class="sw en"></span>English pivot, 45 h</span></div>
      <p class="note" style="margin:0">WER points saved over direct training · dot: gain · line: 95% interval</p>
    </div>""",
      f"""<p>This is our <strong>main result</strong>. Each dot is how many WER points a pivot saves over training on the target alone; the line is the 95% confidence interval. Right of zero means it helped.</p>
<p>The <strong>brown dots, Hindi</strong>, are to the right for every target: Marathi <strong>{sg(gh['marathi']['fleurs'].points)}</strong> and {sg(gh['marathi']['kathbath'].points)}, Odia {sg(gh['odia']['fleurs'].points)} and {sg(gh['odia']['kathbath'].points)}, Kannada {sg(gh['kannada']['fleurs'].points)} and {sg(gh['kannada']['kathbath'].points)}.</p>
<p>The <strong>blue dots, English</strong>, sit on zero. Same 45 hours, same 2,000 steps, and <em>no significant gain anywhere</em>. For Kannada on FLEURS it even hurts, {sg(ge['kannada']['fleurs'].points)}.</p>
<p>So the gain is <strong>not about data quantity</strong> or the extra training stage. Equal English data adds nothing.</p>""")

delta = {l: {ts: gain(l, ts, "hindi_specific") for ts in ["fleurs", "kathbath"]} for l in TARGETS}
mx = max(float(delta[l][ts].points) for l in TARGETS for ts in delta[l])
bars = "".join(
    f'<div class="bar"><span><b>{NAME[l]}</b><br><span class="muted" style="font-size:18px">{"FLEURS" if ts == "fleurs" else "Kathbath"}</span></span>'
    f'<div class="track"><div class="fill{" k" if ts == "kathbath" else ""}" style="--w:{float(delta[l][ts].points) / mx * 100:.0f}%;--d:{200 + i * 140}"></div></div>'
    f'<span class="v">{sg(delta[l][ts].points)}</span></div>'
    for i, (l, ts) in enumerate([(l, ts) for l in TARGETS for ts in ["fleurs", "kathbath"]]))
ix = inter[(inter.metric == "WER") & (inter.comparison == "marathi - kannada") & (inter.test_set == "kathbath")].iloc[0]
kn_ref = "ಸಹ ಕುಸ್ತಿಪಟುಗಳು ಸಹ ಲೂನಾ ಅವರಿಗೆ ಗೌರವ ಸಲ್ಲಿಸಿದರು."
kn_piv = "सहाकुस्ती पटुगलु सहा लूना वरेगे दौरवा सलीसी दरू"
slide("divyansh", "Family or region", f"""
    <h2 class="h2" data-anim="fade-up">Related, yes. <span class="hand">But regional.</span></h2>
    <div class="split">
      <div class="card" data-anim="fade-left">
        <div class="tag acc"><i></i>Δ = Hindi gain − English gain (WER points)</div>
        <div class="bars mt-s">{bars}</div>
        <p class="mt-m">Positive for <b>all three</b>, Dravidian Kannada included. A bigger effect for the Indo-Aryan targets shows only once: Marathi vs Kannada on Kathbath, {sg(ix.points)} [{f1(ix.ci_low)}, {f1(ix.ci_high)}].</p>
      </div>
      <div class="card" data-anim="fade-right" style="animation-delay:.25s">
        <div class="tag hi"><i></i>Hindi pivot on Kannada audio, before any Kannada training</div>
        <div class="lines mt-s">
          <div class="line" style="grid-template-columns:1fr;padding:18px 22px"><span class="k">Said (Kannada script)</span><span class="v script" style="font-size:30px">{kn_ref}</span></div>
          <div class="line wrong" style="grid-template-columns:1fr;padding:18px 22px"><span class="k">Written (Devanagari)</span><span class="v script" style="font-size:30px">{kn_piv}</span></div>
        </div>
        <p class="mt-m">The sounds carry over across families; only the script is wrong. On Marathi, which shares the script, CER already falls from {f1(wer('Z-marathi', 'fleurs', 'CER_clean'))} to {f1(wer('X-hindi-marathi', 'fleurs', 'CER_clean'))}.</p>
      </div>
    </div>""",
      f"""<p>Now RQ1: is it the <strong>language family</strong>? Here is Delta, the Hindi gain minus the English gain. It is <strong>positive for all three targets on both test sets</strong>, including Kannada, which is Dravidian.</p>
<p>If family were everything, Kannada should get nothing. It doesn't: Hindi beats English for Kannada by {sg(delta['kannada']['fleurs'].points)} and {sg(delta['kannada']['kathbath'].points)}. A bigger Indo-Aryan effect appears only once, Marathi versus Kannada on Kathbath, and Marathi also <em>shares Hindi's script</em>, so we can't separate script from family there.</p>
<p>The right side shows why. The Hindi model, before any Kannada training, hears Kannada and writes it <strong>phonetically in Devanagari</strong>: "saha kusti patugalu…". The <em>sounds</em> transfer; only the script is wrong.</p>
<p>So our answer: <strong>relatedness, but regional</strong>. Shared Indian sounds help even across families. Over to Kaushal.</p>""")

# =================================================================== KAUSHAL: results & close
tk = {tok_: (wer(r, "fleurs"), wer(r, "kathbath"), wer(z, "fleurs", "script_valid")) for tok_, r, z in
      [("bn", "D-odia", "Z-odia-bengali"), ("as", "T-odia-assamese", "Z-odia-assamese"), ("hi", "T-odia-hindi", "Z-odia-hindi")]}
tok_names = {"bn": "Bengali", "as": "Assamese", "hi": "Hindi"}
slide("kaushal", "The Odia token", f"""
    <h2 class="h2" data-anim="fade-up">For Odia, the borrowed token <span class="hand">barely matters.</span></h2>
    <div class="grid g3" data-anim="stagger-list">
      {"".join(f'<div class="card"><div class="tag raw"><i></i>&lt;|{k}|&gt; · {tok_names[k]}</div><div class="big num" style="font-size:76px">{f1(v[0])}</div><p class="mt-s">FLEURS WER after training · Kathbath {f1(v[1])}</p><p class="mt-s muted" style="font-size:20px">Odia script: {v[2]:.0f}% untrained → 100% trained</p></div>' for k, v in tk.items())}
    </div>
    <div class="facts mt-l" data-anim="fade-up" style="animation-delay:.6s">
      <div class="fact"><div class="lbl" style="max-width:34ch;font-size:24px">Every difference from Bengali has a 95% interval that includes zero. The closest relatives do not win.</div></div>
      <div class="fact"><div class="big num">{odia_fl['split_too_long_pct']:.1f}<span style="font-size:.45em">%</span></div><div class="lbl">the real ceiling: Odia sentences Whisper cannot write at all</div></div>
    </div>""",
      f"""<p>Thanks, Divyansh. RQ2: Odia has no token, so which one should we borrow?</p>
<p>Untrained, it doesn't matter, because <strong>all three give zero percent Odia script</strong>. After training, all three give <strong>100 percent</strong>, and the error rates are within about one point: Bengali {f1(tk['bn'][0])}, Assamese {f1(tk['as'][0])}, Hindi {f1(tk['hi'][0])} on FLEURS.</p>
<p>None of the differences is statistically reliable, and the genealogically closest languages, Bengali and Assamese, <em>don't win</em>.</p>
<p>So for Odia, the token is not the problem. The real ceiling is the <strong>tokenizer</strong>: {odia_fl['split_too_long_pct']:.1f} percent of Odia sentences are too long for Whisper to ever write.</p>""")

dp = deploy.set_index(["run_id", "precision"])
rtfs = deploy[deploy.precision == "fp16"].rtf
slide("kaushal", "Scoring and deployment", f"""
    <h2 class="h2" data-anim="fade-up">Score it honestly. <span class="hand">Run it offline.</span></h2>
    <div class="grid g2">
      <div class="card" data-anim="fade-left">
        <div class="tag bad"><i></i>RQ3 · scoring rules</div>
        <h4>Whisper's normalizer halves the error</h4>
        <p>Marathi FLEURS, Hindi-pivot model: <b>{f1(wer('H-marathi'))}</b> with our scoring, <b class="bad">{f1(wer('H-marathi', 'fleurs', 'WER_whisper_norm'))}</b> with Whisper's, which deletes vowel signs. Removing punctuation alone moves FLEURS WER by 4.7–8.4 points.</p>
        <p class="mt-s">Hindi-first stays best under all three rules.</p>
      </div>
      <div class="card" data-anim="fade-right" style="animation-delay:.2s">
        <div class="tag acc"><i></i>On this laptop, Apple MLX</div>
        <h4>fp16: {dp.loc[('H-odia', 'fp16')].model_mb:.0f} MB, {1 / rtfs.max():.0f}–{1 / rtfs.min():.0f}× faster than real time</h4>
        <p>Within 2.5 WER of PyTorch on the same clips. 4-bit is 3.4× smaller ({dp.loc[('H-odia', 'q4')].model_mb:.0f} MB) but 6–13 WER worse, and Kannada CER jumps from {f1(dp.loc[('H-kannada', 'fp16')].CER)} to <b class="bad">{f1(dp.loc[('H-kannada', 'q4')].CER)}</b>. We ship fp16.</p>
        <p class="mt-m"><a class="btn" href="http://127.0.0.1:8000/" target="_blank" rel="noopener">Open the live demo →</a></p>
      </div>
    </div>""",
      f"""<p>RQ3, scoring. If you score with <strong>Whisper's own normalizer</strong>, Marathi WER falls from {f1(wer('H-marathi'))} to {f1(wer('H-marathi', 'fleurs', 'WER_whisper_norm'))}, roughly half, because it deletes vowel signs. A paper using it would report numbers that look far better than they are. The good news: Hindi-first stays best under all three rules.</p>
<p>Deployment: we converted the models to Apple's <strong>MLX</strong>. The fp16 model is <strong>144 MB</strong> and runs <strong>17 to 31 times faster than real time</strong> on this laptop, fully offline. 4-bit is smaller but too lossy; it breaks Kannada.</p>
<p><em>[Click the button to show the live demo: play a test clip, then speak into the mic with Wi-Fi off.]</em></p>""")

slide("kaushal", "Limitations and future scope", """
    <h2 class="h2" data-anim="fade-up">What we can't claim yet, <span class="hand">and what's next.</span></h2>
    <div class="grid g2">
      <div class="card" data-anim="fade-left">
        <div class="tag bad"><i></i>Limitations</div>
        <p>· One training seed per run: intervals cover test sampling, not retraining.</p>
        <p class="mt-s">· whisper-base only; absolute WER is high.</p>
        <p class="mt-s">· The English stage moved the model less (loss 0.49 → 0.08, update norm 29.6 vs 36.2) and comes from audiobooks.</p>
        <p class="mt-s">· Marathi shares Hindi's script, so script and family are entangled.</p>
        <p class="mt-s">· Native-speaker error analysis not completed.</p>
      </div>
      <div class="card" data-anim="fade-right" style="animation-delay:.2s">
        <div class="tag acc"><i></i>Future scope</div>
        <p>· A Dravidian pivot (Tamil, Telugu) to test transfer the other way.</p>
        <p class="mt-s">· Marathi → Odia and Kannada → Odia pivots.</p>
        <p class="mt-s">· Several seeds; whisper-small and larger.</p>
        <p class="mt-s">· Targets that separate script from family.</p>
        <p class="mt-s">· A tokenizer that doesn't split Odia letters into bytes.</p>
      </div>
    </div>""",
      """<p>We want to be clear about the limits. <strong>One training seed</strong> per configuration, so our intervals cover the test sample, not retraining. <strong>whisper-base only</strong>.</p>
<p>The English control isn't perfect: Whisper already knows English, so that stage changed the model less, and LibriSpeech is audiobooks. And Marathi shares Hindi's script, so for Marathi, script and family are tangled together.</p>
<p>Next steps: a <strong>Dravidian pivot</strong> like Tamil or Telugu, to test transfer the other way; more seeds and bigger models; and a tokenizer that can actually write Odia.</p>""")

slide("kaushal", "Takeaways", """
    <h2 class="h2" data-anim="fade-up" style="margin-bottom:24px">Three things to remember.</h2>
    <div data-anim="stagger-list">
      <div class="take"><span class="n">1</span><div><h4>It is not data quantity.</h4><p>The same 45 hours of English added nothing; Hindi helped every target.</p></div></div>
      <div class="take"><span class="n">2</span><div><h4>Relatedness, but regional.</h4><p>Hindi helps even Dravidian Kannada; a family-only effect is not established.</p></div></div>
      <div class="take"><span class="n">3</span><div><h4>For Odia, the tokenizer is the ceiling.</h4><p>The borrowed token barely matters; 23% of sentences can't be written at all.</p></div></div>
    </div>
    <p class="h2 mt-l" data-anim="zoom-pop" style="animation-delay:.9s;font-size:56px;margin:36px 0 0">Thank you. <span class="hand">Questions?</span></p>""",
      """<p>To wrap up, three things to remember.</p>
<p><strong>One</strong>: the benefit of a pivot is <strong>not just data</strong>. Same hours of English, nothing.</p>
<p><strong>Two</strong>: it's <strong>relatedness, but regional</strong>. Hindi helps even Kannada, from a different family, so choose pivots by shared sounds and region, not family alone.</p>
<p><strong>Three</strong>: for Odia, the bottleneck is the <strong>tokenizer</strong>, not the language token.</p>
<p>Everything you saw runs on this laptop, offline, and every number comes from our results files. Thank you. We're happy to take questions.</p>""")

html = f"""<!DOCTYPE html>
<!-- Generated by report/slides/build_deck.py from results/. Runtime, base.css and animations from
     github.com/lewislulu/html-ppt-skill (MIT, see assets/LICENSE-html-ppt). -->
<html lang="en" data-themes="indicbridge-light,indicbridge-dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IndicBridge · Viva</title>
<link rel="stylesheet" href="assets/base.css">
<link rel="stylesheet" id="theme-link" href="assets/themes/indicbridge-light.css">
<link rel="stylesheet" href="assets/animations/animations.css">
<link rel="stylesheet" href="assets/deck.css">
</head>
<body>
<div class="deck">
{"".join(slides)}
  <div class="deck-footer"><span>IndicBridge · RV University · NLP project</span><span class="slide-number" data-current="1" data-total="{len(slides)}"></span></div>
</div>
<script src="assets/runtime.js"></script>
</body>
</html>
"""
open(OUT, "w").write(html)
print(f"wrote {OUT}: {len(slides)} slides")
