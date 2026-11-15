"""
server.py - the IndicBridge demo, served from this Mac. Owner: M1.

    .venv/bin/python demo/server.py          # then open http://127.0.0.1:8000

The web app (demo/web, built to demo/web/dist) talks only to this server, and
this server only reads local files and runs MLX on the Mac's GPU. Nothing
leaves the machine: turn Wi-Fi off and it keeps working.
"""
import math
import os
import socket
import threading
import time

import numpy as np
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

import store
from langs import MAX_TOKENS_PER_SEC
from store import LANGUAGES, TEST_SETS, path

app = FastAPI(title="IndicBridge demo")


@app.exception_handler(store.UnknownClip)
def unknown_clip(_, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"detail": exc.args[0]})
mlx_lock = threading.Lock()           # one transcription at a time on the GPU
DIST = path("demo", "web", "dist")


def online():
    """True when the internet is reachable. The demo works either way; this proves it."""
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=0.35).close()
        return True
    except OSError:
        return False


@app.get("/api/status")
def status():
    return {"online": online(), "models": store.models(), "languages": LANGUAGES,
            "test_sets": TEST_SETS, "results": len(store.results())}


@app.get("/api/clips")
def clips(language: str, test_set: str = "fleurs"):
    return {"clips": store.clips(test_set, language)}


@app.get("/api/audio")
def audio(language: str, test_set: str, utt_id: str):
    array, _ = store.clip_audio(test_set, language, utt_id)
    return Response(store.wav_bytes(array), media_type="audio/wav")


@app.get("/api/lanes")
def lanes(language: str, test_set: str = "fleurs", utt_id: str | None = None):
    utt_id = utt_id or store.showcase(language, test_set)
    if utt_id is None:
        raise HTTPException(404, f"No {test_set} test set for {language} yet")
    return {"utt_id": utt_id, "test_set": test_set, "language": language,
            **store.lanes(test_set, language, utt_id)}


@app.post("/api/transcribe")
async def transcribe(model: str = Form(...), language: str = Form(...),
                     token: str = Form(...), precision: str = Form("fp16"),
                     test_set: str | None = Form(None), utt_id: str | None = Form(None),
                     file: UploadFile | None = File(None)):
    """Live MLX transcription of a test clip or of recorded/uploaded audio."""
    import mlx_whisper
    from audio import decode

    entry = store.models().get(model)
    if entry is None:
        raise HTTPException(404, f"Model {model} is not built yet (deploy/build_models.py)")
    reference = None
    if file is not None:
        array = decode(await file.read())
    elif test_set and utt_id:
        array, reference = store.clip_audio(test_set, language, utt_id)
    else:
        raise HTTPException(400, "Send a test clip (test_set + utt_id) or an audio file")
    seconds = len(array) / 16000
    if seconds < 0.3 or float(np.abs(array).max()) < 1e-4:
        raise HTTPException(422, "The recording is silent or shorter than 0.3 s")

    # Same length rule as the scored runs (src/eval_model.py): stop at 1.5x the language's
    # fastest real token rate, so a looping model cannot run on for hundreds of tokens.
    rate = MAX_TOKENS_PER_SEC.get(language, max(MAX_TOKENS_PER_SEC.values()))
    cap = min(440, 10 + math.ceil(1.5 * rate * seconds))
    with mlx_lock:
        t0 = time.perf_counter()
        # Same decoding as deploy/bench_deploy.py: no timestamps (as in training) and
        # Whisper's loop fallback, which the benchmark measured as needed under MLX
        out = mlx_whisper.transcribe(array, path_or_hf_repo=path(entry[precision]["path"]),
                                     language=token, sample_len=cap, without_timestamps=True,
                                     temperature=(0.0, 0.2, 0.4, 0.6), compression_ratio_threshold=2.4,
                                     condition_on_previous_text=False)
        elapsed = time.perf_counter() - t0
    text = out["text"].strip()
    result = {"text": text, "seconds": round(seconds, 2), "elapsed": round(elapsed, 3),
              "rtf": round(elapsed / seconds, 3), "model_mb": entry[precision]["mb"],
              "precision": precision, "online": online()}
    if language in LANGUAGES:
        result["script_valid"] = store.script_share(text, language)
    if reference:
        result.update(reference=reference, **store.align(reference, text))
    return result


@app.get("/api/results")
def results():
    return {"rows": store.results(), "gains": store.gains(), "odia_tokens": store.odia_tokens()}


@app.get("/api/facts")
def facts():
    return {"languages": store.facts()}


@app.get("/api/tokens")
def tokens(text: str):
    return store.tokens(text)


# ---- the viva deck (report/slides), same server so it works offline with the demo ----
DECK = path("report", "slides")
if os.path.isdir(DECK):
    app.mount("/deck", StaticFiles(directory=DECK, html=True), name="deck")


# ---- the built web app; any other path falls back to index.html ----
if os.path.isdir(os.path.join(DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")


@app.get("/{rest:path}")
def spa(rest: str):
    f = os.path.join(DIST, rest)
    if rest and os.path.isfile(f):
        return FileResponse(f)
    index = os.path.join(DIST, "index.html")
    if not os.path.exists(index):
        raise HTTPException(503, "Build the web app first: cd demo/web && npm run build")
    return FileResponse(index)


if __name__ == "__main__":
    os.chdir(path())
    store.facts()          # warm the tokenizer and the facts cache before the first request
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
