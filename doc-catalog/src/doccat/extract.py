"""Tier-0 text extraction: pull an existing text layer, no OCR.

PyMuPDF (import pymupdf / fitz) ships manylinux wheels (no system deps, runs on
python:3.12-slim), extracts text more accurately than pure-python readers, and
repairs malformed PDFs. It also rasterizes pages — reused in Phase 4 for OCR +
thumbnails. A PDF with no text layer (a scan) yields empty pages -> caller
routes it to OCR. Returns [(page_no, text), ...], page_no 1-based.
"""
import pymupdf


def _clean(s):
    """Strip NUL (0x00) — Postgres text columns reject it and PDFs occasionally
    embed it in a text layer."""
    return s.replace("\x00", "")


def pages_from_pdf(path):
    out = []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc):
            out.append((i + 1, _clean(page.get_text().strip())))
    return out


def pages_from_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return [(1, _clean(f.read()))]
