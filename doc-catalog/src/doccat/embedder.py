"""Embedding microservice: bge-base-en-v1.5 on CPU behind one HTTP endpoint.

Isolated in its own pod so the model's memory doesn't crowd the OCR worker. The
model loads once in a background thread at startup (first run downloads weights
to the HF cache on /srv/docs); /healthz reports 503 until it's resident so k8s
readiness gates traffic. /embed returns L2-normalized vectors, so cosine
similarity is a plain dot product downstream. Documents and category prototypes
are both encoded as passages (no instruction prompt) so they compare directly.

Run: uvicorn doccat.embedder:app --host 0.0.0.0 --port 8000
"""
import os
import threading

from fastapi import FastAPI, Response
from pydantic import BaseModel

from . import config

app = FastAPI(title="Embedder")
_model = None
_lock = threading.Lock()


def _load():
    global _model
    with _lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer
            import torch
            torch.set_num_threads(int(os.environ.get("EMBED_THREADS", "4")))
            m = SentenceTransformer(config.EMBED_MODEL, device="cpu")
            # bge-base caps at 512 tokens natively; keep the bound explicit.
            m.max_seq_length = int(os.environ.get("EMBED_MAX_TOKENS", "512"))
            _model = m
    return _model


@app.on_event("startup")
def _startup():
    threading.Thread(target=_load, daemon=True).start()  # non-blocking preload


class EmbedIn(BaseModel):
    texts: list[str]
    is_query: bool = False   # accepted for API compat; gte-base is symmetric (ignored)


@app.get("/healthz")
def healthz(response: Response):
    if _model is None:
        response.status_code = 503
    return {"ok": _model is not None, "model": config.EMBED_MODEL}


@app.post("/embed")
def embed(inp: EmbedIn):
    m = _load()
    vecs = m.encode(inp.texts, normalize_embeddings=True, batch_size=8)
    return {"vectors": [v.tolist() for v in vecs],
            "dim": (len(vecs[0]) if len(vecs) else 0)}
