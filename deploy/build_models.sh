#!/usr/bin/env bash
# Merge each demo adapter, convert to MLX fp16 and 4-bit. Owner: M1.
#   bash deploy/build_models.sh H-odia H-marathi H-kannada P-hindi
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python

# Apple's converter lives in mlx-examples, not in the mlx-whisper wheel.
# It accepts a local Hugging Face folder (config.json + model.safetensors).
if [ ! -d deploy/mlx-whisper-src ]; then
  git clone --depth 1 --filter=blob:none --sparse https://github.com/ml-explore/mlx-examples.git deploy/mlx-whisper-src
  git -C deploy/mlx-whisper-src sparse-checkout set whisper
fi

for RUN in "$@"; do
  $PY deploy/merge_lora.py --adapter "runs/$RUN/adapter" --out "merged/$RUN"
  (cd deploy/mlx-whisper-src/whisper &&
     ../../../$PY convert.py --torch-name-or-path "../../../merged/$RUN" \
        --mlx-path "../../../mlx_models/$RUN-fp16" &&
     ../../../$PY convert.py --torch-name-or-path "../../../merged/$RUN" \
        --mlx-path "../../../mlx_models/$RUN-q4" -q --q-bits 4)
done
du -sh merged/* mlx_models/*
