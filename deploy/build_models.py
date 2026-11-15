"""
build_models.py - turn finished runs into offline MLX models for the demo. Owner: M1.

    python deploy/build_models.py                 # every finished run not built yet, plus zero-shot
    python deploy/build_models.py H-odia P-hindi  # only these

For each run: merge its LoRA adapter into whisper-base, convert it to MLX
fp16 and 4-bit, and record what the demo needs in mlx_models/manifest.json
(run, language, method, pivot, token, sizes).

The conversion follows Apple's mlx-examples/whisper/convert.py (Hugging Face
key names -> OpenAI names -> MLX), written out here so it saves the file name
the installed mlx_whisper loader reads (weights.safetensors).
"""
import glob
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from experiments import load_config, runs  # noqa: E402
from run_queue import resolve_token  # noqa: E402

OUT = os.path.join(ROOT, "mlx_models")
MANIFEST = os.path.join(OUT, "manifest.json")


def dir_mb(path):
    return round(sum(os.path.getsize(f) for f in glob.glob(f"{path}/**", recursive=True)
                     if os.path.isfile(f)) / 1e6, 1)


def merge(run_id, base, out):
    from peft import PeftModel
    from transformers import WhisperForConditionalGeneration
    model = WhisperForConditionalGeneration.from_pretrained(base)
    model = PeftModel.from_pretrained(model, f"{ROOT}/runs/{run_id}/adapter").merge_and_unload()
    model.save_pretrained(out)


HF_TO_OPENAI = [
    ("model.", ""), (".layers", ".blocks"), (".self_attn", ".attn"),
    (".attn_layer_norm", ".attn_ln"), (".encoder_attn.", ".cross_attn."),
    (".encoder_attn_layer_norm", ".cross_attn_ln"), (".final_layer_norm", ".mlp_ln"),
    (".q_proj", ".query"), (".k_proj", ".key"), (".v_proj", ".value"),
    (".out_proj", ".out"), (".fc1", ".mlp1"), (".fc2", ".mlp2"),
    ("embed_positions.weight", "positional_embedding"),
    ("decoder.embed_tokens", "decoder.token_embedding"),
    ("encoder.layer_norm", "encoder.ln_post"), ("decoder.layer_norm", "decoder.ln"),
]


def convert(src, dst, quantize):
    import mlx.core as mx
    import mlx.nn as nn
    from huggingface_hub import snapshot_download
    from mlx.utils import tree_flatten
    from mlx_whisper.whisper import ModelDimensions, Whisper
    from safetensors.numpy import load_file

    path = src if os.path.isdir(src) else snapshot_download(
        src, allow_patterns=["*.json", "model.safetensors"])
    hf = json.load(open(f"{path}/config.json"))
    dims = {"n_mels": hf["num_mel_bins"], "n_audio_ctx": hf["max_source_positions"],
            "n_audio_state": hf["d_model"], "n_audio_head": hf["encoder_attention_heads"],
            "n_audio_layer": hf["encoder_layers"], "n_vocab": hf["vocab_size"],
            "n_text_ctx": hf["max_target_positions"], "n_text_state": hf["d_model"],
            "n_text_head": hf["decoder_attention_heads"], "n_text_layer": hf["decoder_layers"]}

    weights = {}
    for k, v in load_file(f"{path}/model.safetensors").items():
        if k == "proj_out.weight":            # tied to the token embedding
            continue
        for a, b in HF_TO_OPENAI:
            k = k.replace(a, b)
        if k == "encoder.positional_embedding":   # MLX computes the sinusoids itself
            continue
        w = mx.array(v)
        if "conv" in k and w.ndim == 3:
            w = w.swapaxes(1, 2)
        weights[k] = w.astype(mx.float16)

    model = Whisper(ModelDimensions(**dims), mx.float16)
    # Every model weight must come from the checkpoint; only alignment_heads
    # (word timestamps, unused here) is MLX's own
    expected = {k for k, _ in tree_flatten(model.parameters())} - {"alignment_heads"}
    assert expected == set(weights), f"key mismatch: {sorted(expected ^ set(weights))[:6]}"
    model.load_weights(list(weights.items()), strict=False)
    if quantize:
        nn.quantize(model, group_size=64, bits=4)
        dims["quantization"] = {"group_size": 64, "bits": 4}

    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    mx.save_safetensors(f"{dst}/weights.safetensors", dict(tree_flatten(model.parameters())))
    with open(f"{dst}/config.json", "w") as f:
        json.dump({**dims, "model_type": "whisper"}, f, indent=2)


def main():
    cfg = load_config(os.path.join(ROOT, "config.json"))
    base = cfg["base_model"]
    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    grid = {r["id"]: r for r in runs()}

    wanted = sys.argv[1:] or (["zeroshot"] + [
        rid for rid, r in grid.items()
        if r["kind"] == "train" and os.path.exists(f"{ROOT}/runs/{rid}/DONE")])

    for rid in wanted:
        if rid in manifest and not sys.argv[1:]:
            continue
        if rid == "zeroshot":
            src, meta = base, {"language": "all", "method": "zeroshot", "pivot": "none",
                               "token": "per language"}
        else:
            r = grid[rid]
            src = f"{ROOT}/merged/{rid}"
            merge(rid, base, src)
            meta = {"language": r["language"], "method": r["method"], "pivot": r["pivot"],
                    "token": resolve_token(r)}
        for kind, q in [("fp16", False), ("q4", True)]:
            convert(src, f"{OUT}/{rid}-{kind}", q)
        manifest[rid] = {**meta, "base": base,
                         "fp16": {"path": f"mlx_models/{rid}-fp16", "mb": dir_mb(f"{OUT}/{rid}-fp16")},
                         "q4": {"path": f"mlx_models/{rid}-q4", "mb": dir_mb(f"{OUT}/{rid}-q4")}}
        print(f"{rid}: fp16 {manifest[rid]['fp16']['mb']} MB, q4 {manifest[rid]['q4']['mb']} MB")
        os.makedirs(OUT, exist_ok=True)
        with open(MANIFEST, "w") as f:
            json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
