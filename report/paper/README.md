# IndicBridge IEEE paper: team guide

## Open it in Overleaf
1. Overleaf, then New Project, then Upload Project, and choose `IndicBridge_Paper_Overleaf.zip`.
2. Compile with the default pdfLaTeX. Every red **[WRITE: …]** marker is a place for your own sentences.
3. In the source, each marker has `% FACT:` lines under it: the verified numbers, and which project file each comes from. They never print. Delete each red marker once your text replaces it.

## Rules that protect your marks
- **Write every sentence yourselves.** The fact notes are deliberately terse. Don't paste them as sentences, and don't run your text through a paraphrasing tool. Turnitin's AI check runs on the whole paper, so sections I–III (carried over from Review-1) should be reworded in your own voice too.
- **Never type a number by hand.** All tables and Fig. 2 come from `build_assets.py`, which reads the results files. If you quote a number in the text, take it from a table or a `% FACT:` line.
- **Don't claim what wasn't measured.** The `% DO NOT CLAIM:` lines mark the traps. The main one: the data shows relatedness helps, but a *family-specific* extra is not established.
- **Fix every `% FIX:` line in sections I–III.** The study used whisper-base (not whisper-small), Kathbath (not Common Voice), and one M4 laptop (not free-tier GPUs).
- **Plagiarism (target under 10%):** paraphrase the related work properly, and quote nothing. Ask your teacher whether your own Review-1 submission is excluded from the Turnitin match. If it isn't, sections I–III must be reworded.

## Page plan: 6 pages
The skeleton is already 7 pages. That count comes from a wider fallback font; Overleaf's Times is narrower. Your text will add about 2 pages, so to land at 6:
1. **Literature Review (II):** cut from about 1,250 words to about 650. Keep each subsection heading, with 2–3 sentences each.
2. **Table I:** keep it, but you can drop the "Dataset / Evaluation" column or the four least relevant rows. Don't delete any reference.
3. **Write to the word budgets in the red markers**, about 1,800 words in total for sections IV–VII plus the abstract.
4. **If you're still over:** replace Table VII (scoring rules) and Table VIII (deployment) with one sentence each.

## Suggested split (about 1 to 1.5 hours each)
| Person | Writes |
|---|---|
| Gourab | Abstract, IV Problem Statement, VI-B (main answer), VI-C |
| Parth | V-A to V-D (design, data, model, Odia token), plus trimming II |
| Divyansh | V-E to V-H (metrics, statistics, deployment, error protocol), VI-E, VI-F |
| Kaushal | VI-A, VI-D, VI-G (error analysis), VI-H Limitations, VII Conclusion |

## Error analysis table (VI-G)
1. Each of you fills in your language sheet in `results/error_analysis/<language>_50.csv`. The README in that folder explains the categories.
2. Then run `.venv/bin/python report/paper/error_tally.py`. It prints how many rows each sheet has, and writes `tables/errors.tex`.
3. Upload `tables/errors.tex` to Overleaf and uncomment `\input{tables/errors}` in section VI-G.
If any sheet is incomplete, report only the finished languages, or move the analysis to Future Scope.

## Regenerating tables and the figure
`PYTHONPATH=src .venv/bin/python report/paper/build_assets.py` (run from the repo root after `src/analysis.py`).

## References
All 24 were checked against Crossref and the publishers. Review-1 had Pillai et al. as 2025; it is
**ACM TALLIP vol. 25, no. 8, 2026**, DOI 10.1145/3813800. Page ranges were added for Ferraz et al. and IndicVoices.
New since Review-1: LibriSpeech, Bisani & Ney (bootstrap CIs), Transformers, PEFT, MLX. Keep all of them: the teacher asked for the earlier references to stay.
