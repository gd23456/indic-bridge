"""
audio.py - decode/encode helpers shared by data prep, training and eval.

Everything inside the project is 16 kHz mono, stored as FLAC bytes.
"""
import io

import librosa
import numpy as np
import soundfile as sf

TARGET_SR = 16000     # Whisper always expects 16 kHz


def decode(audio_bytes):
    """Any wav/flac/mp3 bytes -> float32 mono array at 16 kHz."""
    data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
    data = data.mean(axis=1)
    if sr != TARGET_SR:
        data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR, res_type="soxr_hq")
    return data.astype(np.float32)


def encode_flac(array):
    buf = io.BytesIO()
    sf.write(buf, array, TARGET_SR, format="FLAC", subtype="PCM_16")
    return buf.getvalue()


def to_flac_16k(audio_bytes):
    """Re-encode one clip; returns (flac_bytes, seconds) or (None, 0) if unreadable."""
    try:
        arr = decode(audio_bytes)
    except Exception:
        return None, 0.0
    return encode_flac(arr), len(arr) / TARGET_SR
