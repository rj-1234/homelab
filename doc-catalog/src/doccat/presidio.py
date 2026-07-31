"""PII analyzer microservice: Microsoft Presidio on CPU behind one HTTP endpoint.

Own pod (like the embedder) so the spaCy model + analyzer don't crowd the other
workers, and so PII recognition stays on-node — nothing here egresses. Presidio
fuses three signals per hit: pattern recognizers (built-in + our custom ones in
recognizers.py), a spaCy NER backbone for context, and validators (Luhn on cards,
etc.), returning entity_type + span + a 0-1 score. The field-worker calls /analyze
with a document's text and turns the spans into candidate vault fields.

Run: uvicorn doccat.presidio:app --host 0.0.0.0 --port 8000
"""
import os
import threading

from fastapi import FastAPI, Response
from pydantic import BaseModel

from .recognizers import custom_recognizers

app = FastAPI(title="Presidio PII Analyzer")
_engine = None
_lock = threading.Lock()

# spaCy model backing the NER context. Small by default (light pod); override with
# PRESIDIO_SPACY_MODEL=en_core_web_lg or a transformer model if recall is weak.
SPACY_MODEL = os.environ.get("PRESIDIO_SPACY_MODEL", "en_core_web_sm")


def _load():
    global _engine
    with _lock:
        if _engine is None:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            provider = NlpEngineProvider(nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": SPACY_MODEL}],
            })
            eng = AnalyzerEngine(nlp_engine=provider.create_engine())
            for rec in custom_recognizers():
                eng.registry.add_recognizer(rec)
            _engine = eng
    return _engine


@app.on_event("startup")
def _startup():
    threading.Thread(target=_load, daemon=True).start()   # non-blocking preload


class AnalyzeIn(BaseModel):
    text: str
    score_threshold: float = 0.35


@app.get("/healthz")
def healthz(response: Response):
    if _engine is None:
        response.status_code = 503
    return {"ok": _engine is not None, "model": SPACY_MODEL}


@app.post("/analyze")
def analyze(inp: AnalyzeIn):
    """Return PII spans with the matched text sliced out, so the caller stores the
    value without re-reading the document."""
    eng = _load()
    results = eng.analyze(text=inp.text, language="en",
                          score_threshold=inp.score_threshold)
    out = []
    for r in results:
        out.append({
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": round(float(r.score), 3),
            "text": inp.text[r.start:r.end],
        })
    return {"entities": out}
