# File contract

These files have ONE owner. Nobody else edits them. If you need a
change, message the owner. If you find a bug, message the owner —
do not fix it locally.

| File                | Owner | Changed by anyone else? |
|---------------------|-------|-------------------------|
| src/normalize.py    | M2    | NO                      |
| src/evaluate.py     | M2    | NO                      |
| src/data_prep.py    | M3    | NO                      |
| src/eval_model.py   | M4    | NO                      |

Single-owner files, edited freely by their owner:
train_lora.py, run_queue.py, experiments.py, bench.py (M1); analysis.py (M4);
deploy/* (M1); report/* (all)

## Verification

Before any evaluation run:

    python src/normalize.py --checksum

Reference checksum:

    CONTRACT_VERSION: 3.0.0
    SHA256[:16]     : dd96f6230b6fbdf1

Windows members: if your checksum differs but the file looks identical,
it is line endings — run `git config --global core.autocrlf input` and re-clone.
