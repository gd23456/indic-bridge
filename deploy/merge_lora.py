"""
merge_lora.py - fold a LoRA adapter into whisper-base so it can be
converted and quantized. Owner: M1.

    python deploy/merge_lora.py --adapter runs/H-odia/adapter --out merged/H-odia
"""
import argparse

from peft import PeftModel
from transformers import WhisperForConditionalGeneration, WhisperProcessor

p = argparse.ArgumentParser()
p.add_argument("--base",    default="openai/whisper-base")
p.add_argument("--adapter", required=True)
p.add_argument("--out",     required=True)
a = p.parse_args()

base = WhisperForConditionalGeneration.from_pretrained(a.base)
model = PeftModel.from_pretrained(base, a.adapter).merge_and_unload()
model.save_pretrained(a.out)
WhisperProcessor.from_pretrained(a.base).save_pretrained(a.out)
print("Merged model saved to", a.out)
