"""Runtime config from env. All paths under DOCS_ROOT (the ZFS dataset)."""
import os
from pathlib import Path

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://doccat:doccat@localhost:5432/doccat"
)

DOCS_ROOT = Path(os.environ.get("DOCS_ROOT", "/srv/docs"))

INBOX = DOCS_ROOT / "inbox"
STAGING = INBOX / ".staging"
PROCESSED = INBOX / ".processed"
FAILED = INBOX / ".failed"
BLOBS = DOCS_ROOT / "blobs"

# Reject files larger than this (re-checked here even though FileBrowser caps it).
MAX_BYTES = int(os.environ.get("MAX_BYTES", str(100 * 1024 * 1024)))  # 100 MB

# Reconcile scan cadence (source of truth). inotify is a later latency add-on.
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", "30"))

# Quiescence guard: only claim a file once size+mtime are stable across two
# scans AND mtime is at least this old (avoids hashing partial uploads).
QUIESCENCE_AGE = int(os.environ.get("QUIESCENCE_AGE", "10"))

# --- OCR (Phase 4) ----------------------------------------------------------
# PaddleOCR runs locally (CPU). Pages whose mean recognition confidence falls
# below the threshold escalate to Claude vision (if ANTHROPIC_API_KEY is set).
OCR_DPI = int(os.environ.get("OCR_DPI", "220"))          # pdf page raster DPI
OCR_CONF_THRESHOLD = float(os.environ.get("OCR_CONF_THRESHOLD", "0.6"))
CLAUDE_VISION_MODEL = os.environ.get("CLAUDE_VISION_MODEL", "claude-opus-5")
