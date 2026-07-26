"""OCR (Phase 4): PaddleOCR locally, escalate low-confidence pages to Claude.

Heavy imports (paddleocr, anthropic, PIL) are done lazily so the rest of the
package still imports on a plain interpreter without them. Pages are rasterized
with PyMuPDF; HEIC/other images are normalized to PNG (pillow + pillow-heif).
"""
import base64
import io

import pymupdf

from . import config

_engine = None


def _paddle():
    global _engine
    if _engine is None:
        from paddleocr import PaddleOCR
        _engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _engine


def _pdf_page_pngs(path, dpi):
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc):
            yield i + 1, page.get_pixmap(dpi=dpi).tobytes("png")


def _image_png(path):
    from PIL import Image
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()   # lets Image.open read HEIC
    except Exception:  # noqa: BLE001 — heif optional
        pass
    with Image.open(path) as im:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()


def pages_for(path, mime):
    """Yield (page_no, png_bytes) for a document's blob."""
    if mime == "application/pdf":
        yield from _pdf_page_pngs(path, config.OCR_DPI)
    elif mime.startswith("image/"):
        yield 1, _image_png(path)


def paddle_png(png_bytes):
    """Return (text, mean_confidence) for one page image via PaddleOCR."""
    import numpy as np
    from PIL import Image
    img = np.array(Image.open(io.BytesIO(png_bytes)).convert("RGB"))
    result = _paddle().ocr(img, cls=True)
    lines, confs = [], []
    for page in result or []:
        for box_text in page or []:
            text, score = box_text[1]           # entry = [box, (text, score)]
            lines.append(text)
            confs.append(float(score))
    return "\n".join(lines), (sum(confs) / len(confs) if confs else 0.0)


def claude_png(png_bytes):
    """Transcribe one page image with Claude vision. Returns text ('' on refusal)."""
    import anthropic
    client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
    b64 = base64.b64encode(png_bytes).decode()
    resp = client.messages.create(
        model=config.CLAUDE_VISION_MODEL,
        max_tokens=8000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64", "media_type": "image/png", "data": b64}},
            {"type": "text", "text":
                "Transcribe ALL text in this document image verbatim, preserving "
                "reading order and line breaks. Output only the transcription, "
                "with no commentary."},
        ]}],
    )
    if resp.stop_reason == "refusal":
        return ""
    return "".join(b.text for b in resp.content if b.type == "text").strip()
