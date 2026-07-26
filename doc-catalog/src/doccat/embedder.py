"""Embedding microservice: Qwen3-Embedding-0.6B on CPU behind one HTTP endpoint.

Isolated in its own pod so the ~0.6B model's memory doesn't crowd the OCR
worker. The model loads once in a background thread at startup (first run
downloads weights to the HF cache on /srv/docs); /healthz reports 503 until it's
resident so k8s readiness gates traffic. /embed returns L2-normalized vectors,
so cosine similarity is a plain dot product downstream.

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
            # Bound sequence length: Qwen supports 32k but fp32 CPU activations on
            # a multi-thousand-token input OOM the pod. ~2k tokens is ample for
            # classification and keeps memory flat.
            m.max_seq_length = int(os.environ.get("EMBED_MAX_TOKENS", "2048"))
            _model = m
    return _model


@app.on_event("startup")
def _startup():
    threading.Thread(target=_load, daemon=True).start()  # non-blocking preload


class EmbedIn(BaseModel):
    texts: list[str]
    is_query: bool = False   # queries get Qwen's 'query' instruction prompt


@app.get("/healthz")
def healthz(response: Response):
    if _model is None:
        response.status_code = 503
    return {"ok": _model is not None, "model": config.EMBED_MODEL}


@app.post("/embed")
def embed(inp: EmbedIn):
    m = _load()
    kw = {"normalize_embeddings": True, "batch_size": 4}
    if inp.is_query:
        kw["prompt_name"] = "query"
    vecs = m.encode(inp.texts, **kw)
    return {"vectors": [v.tolist() for v in vecs],
            "dim": (len(vecs[0]) if len(vecs) else 0)}
