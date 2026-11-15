---
name: IndicBridge
description: An offline viva demo where real Indic test sentences fly out of a paper tunnel and every Whisper model writes them, wrong words marked.
colors:
  brand-indigo: "#4f2cf5"
  brand-indigo-dark: "#9d8cff"
  brand-ink: "#ffffff"
  brand-tint: "#ecebfe"
  alert-red: "#cf2a1d"
  alert-red-dark: "#ff6257"
  alert-bg: "#fdecea"
  pivot-hindi-gold: "#985a0e"
  pivot-english-blue: "#2a69ac"
  glow-a: "#8f7dff"
  glow-b: "#c3a6ff"
  glow-c: "#6ec3ff"
  paper: "#f4f4f2"
  sunken: "#ebebe8"
  surface: "#ffffff"
  line: "#e2e2de"
  line-strong: "#c9c9c3"
  dot: "#cdcdd3"
  ink: "#111113"
  muted: "#5c5c63"
  paper-dark: "#0a0a0c"
  surface-dark: "#141418"
  ink-dark: "#f1f1f3"
typography:
  display:
    fontFamily: "Monaspace Xenon, Monaspace Neon, ui-monospace, monospace"
    fontSize: "5.75rem"
    fontWeight: 800
    lineHeight: 0.98
    letterSpacing: "-0.04em"
    fontVariation: "'wdth' 112"
  headline:
    fontFamily: "Monaspace Xenon, Monaspace Neon, ui-monospace, monospace"
    fontSize: "3.5rem"
    fontWeight: 800
    lineHeight: 0.98
    letterSpacing: "-0.04em"
    fontVariation: "'wdth' 112"
  hand:
    fontFamily: "Monaspace Radon, Monaspace Neon, ui-monospace, monospace"
    fontWeight: 500
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Monaspace Neon, Noto Sans Devanagari Variable, Noto Sans Kannada Variable, Noto Sans Oriya Variable, ui-monospace, monospace"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.625
  script:
    fontFamily: "Noto Sans Oriya Variable, Noto Sans Devanagari Variable, Noto Sans Kannada Variable, Monaspace Neon, monospace"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "Monaspace Neon, ui-monospace, monospace"
    fontSize: "0.6875rem"
    fontWeight: 400
    letterSpacing: "0.08em"
  data:
    fontFamily: "Monaspace Neon, ui-monospace, monospace"
    fontSize: "0.875rem"
    fontFeature: "'tnum'"
rounded:
  chip: "5px"
  tooltip: "8px"
  menu: "12px"
  card: "14px"
  pill: "999px"
spacing:
  gutter: "20px"
  gutter-wide: "32px"
  card-pad: "20px"
  card-pad-wide: "28px"
  block: "48px"
  block-wide: "56px"
  section: "112px"
  section-wide: "144px"
  container: "72rem"
components:
  button-primary:
    backgroundColor: "{colors.brand-indigo}"
    textColor: "{colors.brand-ink}"
    rounded: "{rounded.pill}"
    size: "44px"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
  segmented-on:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
  segmented-off:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
  icon-button:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    size: "36px"
  select:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "8px 32px 8px 14px"
  input-filter:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
    padding: "{spacing.card-pad}"
  tunnel-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "16px"
  token-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.chip}"
    padding: "0 6px"
  byte-chip:
    backgroundColor: "{colors.sunken}"
    textColor: "{colors.muted}"
    rounded: "{rounded.chip}"
    padding: "0 4px"
---

# Design System: IndicBridge

## Overview

**Creative North Star: "The Test Set Is the Stage"**

IndicBridge is a lit-room projector piece: warm grey paper, white cards, 1px graphite lines and near-black ink, with one electric indigo carrying identity, the primary action and the orb. The hero is a full-height paper stage with a dot grid and two depth rings centred on a vanishing point at 46% of the height. Out of that point, real FLEURS test sentences in Devanagari, Kannada and Odia drift toward the viewer on white cards, and the MorphOrb sits at the centre turning speech into one more card. Everything below the hero is quiet editorial paper: one heavy slab headline per section, one figure, very little text.

Type is GitHub Next's Monaspace superfamily, self-hosted so the page renders with the network off. Xenon (slab), wide and heavy, is the display voice; Neon carries everything else; Radon, a handwriting face, takes one phrase per headline and the occasional margin note. Indic scripts fall through to bundled Noto faces at reading size. The world explicitly rejects the team's Neralu hackathon site: no deep-space starfield, no mint neon, no dark-by-default.

Colour only appears where it means something. Indigo is the product and the action; red is a wrong word or a failure the presenter must see; gold and blue identify the Hindi and English pivots in data and nowhere else.

**Key Characteristics:**
- Light paper by default (#f4f4f2), dark theme on request (#0a0a0c with a lighter indigo).
- One accent, indigo, for identity, primary action and the orb.
- Monaspace throughout: Xenon display, Neon text, Radon for one handwritten phrase.
- 1px lines and white cards; depth comes from the tunnel's real perspective, not from stacked shadows.
- Every transcript carries the same three error marks, which ignite once when they land.

## Colors

A neutral paper-and-graphite field with a single electric indigo and strictly semantic data colours.

### Primary
- **Electric Indigo** (brand-indigo; brand-indigo-dark in the dark theme): the wordmark, the orb and its dot ramp, the mic button, the inner depth ring and stage wash, focus outlines, selection, active hover borders, the edge of your own tunnel cards, and the Radon phrase in every headline.
- **Indigo Tint** (brand-tint): the selected row in the bench clip list. Never a large fill.

### Secondary
- **Alert Red** (alert-red; alert-red-dark in dark): substituted and inserted words, the orb pill's failure flash, error text. It marks a wrong word or a failure and nothing else.

### Tertiary
- **Hindi Gold** (pivot-hindi-gold) and **English Blue** (pivot-english-blue): series colours for the two pivots in the results chart, legend and method swatches. Validated against white and against the dark surface. Data only.
- **Orb Glow** (glow-a, glow-b, glow-c): tint only the orb's aurora and travelling ring. Never used on page chrome.

### Neutral
- **Paper** (paper): page and stage background.
- **Sunken Paper** (sunken): row hover, byte chips.
- **Card White** (surface): cards, tunnel cards, pills, tooltips, menus.
- **Hairline** (line): default 1px dividers, card borders, gridlines.
- **Graphite Line** (line-strong): control borders, the dashed outer ring, the chart zero line, scrollbars.
- **Dot Grey** (dot): the hero dot grid.
- **Ink** (ink): text and transcripts; also the selected segment's fill.
- **Muted Ink** (muted): secondary text, metadata, dropped-word ghosts.

### Named Rules
**The Colour Carries Meaning Rule.** Indigo is identity and action, red is a wrong word or a failure, gold and blue are the pivots in data. A colour that does not carry one of those meanings does not appear.

**The One Accent Rule.** There is one accent. Glow tints live inside the orb; pivot colours live inside data. Neither leaks into chrome.

## Typography

**Display Font:** Monaspace Xenon (with Monaspace Neon, ui-monospace)
**Body Font:** Monaspace Neon (with bundled Noto Sans Devanagari/Kannada/Oriya, ui-monospace)
**Hand Font:** Monaspace Radon (with Monaspace Neon)
**Script Font:** Noto Sans Oriya / Devanagari / Kannada Variable

**Character:** A single monospaced superfamily read three ways: a heavy, stretched slab that shouts the question, an even code voice that states the facts, and a handwriting cut that answers back in indigo.

### Hierarchy
- **Display** (Xenon 800, stretch 112%, -0.04em, line-height 0.98, 2.6rem / 4.25rem / 5.75rem by breakpoint, balanced): the hero H1 only.
- **Headline** (same face and settings, 2.25rem / 3.5rem): one per section.
- **Hand** (Radon 500, -0.03em): exactly one phrase inside each headline, coloured indigo there; elsewhere a short muted margin note or figure caption.
- **Body** (Neon 400, 15px root, relaxed leading, max ~34rem under the hero): supporting lines, kept to one sentence where possible.
- **Script** (Noto, line-height 1.7, 1.0625rem in lanes, 1.375rem for a live transcript, up to 1.875rem for the Odia showcase sentence): every Indic transcript. Breaks anywhere so hallucinated runs wrap instead of widening the page.
- **Label** (Neon 0.6875rem, uppercase, 0.08em tracking; 0.12em on tunnel cards): table column headers and the language name on tunnel cards only.
- **Data** (Neon, tabular figures): every number that is compared.

### Named Rules
**The One Hand Phrase Rule.** Each headline switches to Radon for exactly one phrase, and that phrase is the indigo in the heading. Radon never sets a full heading or a paragraph.

**The Script at Reading Size Rule.** Indic text is never smaller than 1.0625rem in a transcript and always sits in the bundled Noto faces, never a system fallback.

## Layout

Sections sit in a centred container (72rem) with 20px gutters, 32px from the small breakpoint. Vertical rhythm is generous: 112px section padding, 144px from the small breakpoint; headline to figure 48 to 56px. The hero is full-height with everything centred on one vanishing point at 50% / 46%: the dot grid (28px pitch, masked to an ellipse), the indigo wash, both rings, the tunnel and the orb. The headline sits above that point with a paper veil behind it so cards never cross the words. The top bar floats over the stage. Under 768px the tunnel shows eight test cards and a shallower perspective (900 vs 1200), nav links collapse into a round menu button, and lane tables stack each row (model, WER and CER on one line, transcript full width below). The results chart drops family notes below 560px of width.

## Elevation & Depth

Depth is spatial, not shadowed. The hero builds it with real 3D perspective: cards travel from deep z toward the viewer, rotate slightly, pan against the pointer and fade near the top bar. Elsewhere surfaces are flat white on paper with a 1px line. One soft float shadow exists for things that genuinely hover (tunnel cards, the mobile menu, the chart tooltip); the orb carries its own softer light-theme shadows. In the dark theme tunnel cards lift to a lighter surface with the strong line so they read as cards, not floating text.

### Shadow Vocabulary
- **Float** (`0 22px 48px -28px rgba(17,17,19,0.3), 0 1px 2px rgba(17,17,19,0.05)` light; `0 26px 60px -28px rgba(0,0,0,0.85)` dark): tunnel cards, menu, tooltip.
- **Orb pill** (`0 14px 36px -22px rgba(17,17,19,0.18)` light): the resting orb input.
- **Orb card** (`0 22px 54px -30px rgba(17,17,19,0.16), 0 1px 2px rgba(17,17,19,0.06)` light): the unfolded result card.

### Named Rules
**The Perspective Not Shadow Rule.** The page earns depth from the tunnel's perspective and the two rings. Section cards stay flat; only floating things get the float shadow.

**The Step Back Rule.** While the orb holds a result, the tunnel slows to 0.18 of its pace and dims to 0.28 opacity so the card reads.

## Shapes

Soft rectangles and full pills. Cards and tunnel cards use a gentle 14px radius; the mobile menu 12px; tooltips 8px; token and byte chips a tight 5px. Every control (buttons, selects, segmented groups, the filter input, the orb pill and mic) is a full pill or circle. Borders are 1px everywhere except your own tunnel card, which takes a 1.5px indigo edge. The hero rings are true circles: inner 48vmin solid indigo at 22%, outer 78vmin dashed graphite at 70% opacity.

## Components

### Buttons
Quiet outlines; one filled indigo action per surface.
- **Shape:** full pill, or a circle for icon buttons (36px) and the mic (44px).
- **Primary:** indigo fill, white icon (the mic in the orb pill; the bench play button).
- **Outline:** transparent, graphite border, ink text, 6px 14px; hover turns the border indigo.
- **Press:** every pressable scales to 0.97 on active (140ms, ease-out-quint), colours ease over 150ms.
- **Focus:** 2px indigo outline, 2px offset.

### Chips
- **Segmented control:** a pill outline holding pill options; the selected option is ink-filled with paper text, others muted until hover.
- **Token chips:** white with a graphite border, script text at 0.8125rem. **Byte chips:** sunken paper, muted hex in Neon at 0.6875rem, no border.

### Cards / Containers
- **Corner Style:** 14px.
- **Background:** card white on paper.
- **Shadow Strategy:** flat; see Elevation.
- **Border:** 1px hairline.
- **Internal Padding:** 20px, 24 to 28px on wider screens.

### Inputs / Fields
- **Select:** native select in a pill, graphite border, drawn chevron, hover border indigo; transparent inside the orb pill.
- **Filter:** pill on paper with a hairline border, muted placeholder.

### Navigation
Wordmark (the three-pier arch drawn in indigo beside "IndicBridge" in Xenon 800) left; three lowercase section links in muted Neon at 0.8125rem, ink and underlined on hover; a live network dot (hollow when online, indigo when offline); a round theme toggle. Under 768px the links fold into a round menu button opening a 12px card.

### Tunnel Card (signature)
A 4:5 white card, 16px padding: uppercase language name and tabular duration at the top, the sentence in its script clamped to six lines, a muted provenance note at the bottom. Your own cards ("you, just now", "played just now") take a 1.5px indigo edge, an indigo Radon note, the open lanes either side of the headline, and a layer above the test cards.

### Error Marks (signature)
The same three marks on every transcript: a substituted word is red with a solid underline, an inserted word red with a dashed underline, a dropped word a struck, muted, 0.86em ghost of the reference. When a lane lands its errors ignite once, left to right (40ms per word, 900ms), then stay marked. The light theme drops the glow and draws underlines at full strength; reduced motion shows the final state. A key explaining the three marks appears wherever transcripts are compared.

### MorphOrb (signature)
The pill at the bottom of the stage (language select, level meter, test clip button, indigo mic) unfolds into the result card. Its dot ramp runs from ink to indigo on light and from near-white to the lighter indigo on dark; its aurora uses only the glow tints.

## Do's and Don'ts

### Do:
- **Do** keep the page light by default on paper (#f4f4f2) and offer dark only through the toggle.
- **Do** set every headline in Xenon 800 at 112% stretch and -0.04em, with exactly one phrase in indigo Radon.
- **Do** use red only for a wrong word or a failure the presenter must see.
- **Do** use gold and blue only to identify the Hindi and English pivots in data.
- **Do** render Indic text in the bundled Noto faces at 1.0625rem or larger, with tabular figures for every compared number.
- **Do** centre every hero layer on the vanishing point at 50% / 46%.
- **Do** mark every transcript with the same three error marks and the key that explains them.

### Don't:
- **Don't** use a deep-space starfield, mint neon, or a dark-by-default page; the world must not resemble the Neralu hackathon site.
- **Don't** introduce a second accent or let the orb's glow tints into chrome.
- **Don't** set full headings or paragraphs in Radon.
- **Don't** put shadows on flat section cards; depth belongs to the tunnel.
- **Don't** use system display faces; Monaspace is self-hosted so the page works offline.
- **Don't** use emoji or "AI-powered" copy.
