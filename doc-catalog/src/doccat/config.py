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

# --- Gmail ingestion --------------------------------------------------------
# Each account is a google "authorized_user" token JSON (client id/secret +
# refresh token, gmail.readonly scope), mounted read-only as token-<label>.json.
# Accounts are discovered from the files — no manual seeding.
GMAIL_TOKENS_DIR = Path(os.environ.get("GMAIL_TOKENS_DIR", "/secrets/gmail"))
GMAIL_POLL_INTERVAL = int(os.environ.get("GMAIL_POLL_INTERVAL", "300"))   # 5 min
# First backfill is bounded so we don't pull an entire mailbox on account 1.
GMAIL_INITIAL_QUERY = os.environ.get("GMAIL_INITIAL_QUERY", "has:attachment newer_than:1y")
# Skip small attachments (signature logos/icons). 0 disables the floor.
GMAIL_MIN_ATTACH_BYTES = int(os.environ.get("GMAIL_MIN_ATTACH_BYTES", str(8 * 1024)))

# Only ingest document-type attachments — newsletters attach images. An
# attachment qualifies if its email-declared MIME is in GMAIL_ATTACH_MIME OR its
# filename ends with one of GMAIL_ATTACH_EXT. Everything else (jpg/png/gif) is
# skipped. Sender allow/deny rules (sender_rule table) further restrict senders.
GMAIL_ATTACH_MIME = set(filter(None, os.environ.get(
    "GMAIL_ATTACH_MIME",
    "application/pdf,"
    "application/msword,"
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
    "application/vnd.ms-excel,"
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
).split(",")))
GMAIL_ATTACH_EXT = tuple(filter(None, os.environ.get(
    "GMAIL_ATTACH_EXT", ".pdf,.doc,.docx,.xls,.xlsx").split(",")))

# --- Embedding + semantic tagging (Phase 7) ---------------------------------
# Qwen3-Embedding-0.6B (1024-dim, 32k context) hosted in a dedicated CPU pod.
EMBEDDER_URL = os.environ.get("EMBEDDER_URL", "http://embedder:8000")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "Qwen/Qwen3-Embedding-0.6B")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "1024"))
# Cap the doc text sent for the doc-level vector (chars). 32k ctx handles it,
# but keep a sane bound. Pages are embedded separately as chunks.
EMBED_MAX_CHARS = int(os.environ.get("EMBED_MAX_CHARS", "2500"))
# Cosine floor for assigning a top-level category (multi-label). Tune from the
# UI feedback loop; zero-shot prototypes sit lower than fitted centroids.
CLASSIFY_THRESHOLD = float(os.environ.get("CLASSIFY_THRESHOLD", "0.35"))
# Once a category has at least this many user-confirmed documents, its prototype
# switches from the zero-shot description to the centroid of those documents'
# vectors — accuracy that improves as you correct tags, no LLM.
CLASSIFY_MIN_CENTROID = int(os.environ.get("CLASSIFY_MIN_CENTROID", "2"))
# Embed each page as its own chunk (for page-level semantic search). Off by
# default: the doc-level vector alone drives tagging, and per-page embedding is
# the slow part on CPU (a 9-page doc = 10 encodes). Enable once search is wired.
EMBED_PAGES = os.environ.get("EMBED_PAGES", "false").lower() in ("1", "true", "yes")

# --- Worker specialization --------------------------------------------------
# Which job stages this worker process claims, and whether it scans the inbox /
# polls Gmail. The default is an all-in-one worker; deployments split it:
#   main worker  -> WORKER_STAGES=text,ocr   WORKER_INGEST=true
#   embed worker -> WORKER_STAGES=embed       WORKER_INGEST=false
# so a slow embedding never blocks text/OCR (they drain the same queue in
# parallel via FOR UPDATE SKIP LOCKED).
WORKER_STAGES = tuple(filter(None, os.environ.get(
    "WORKER_STAGES", "text,ocr,embed").split(",")))
WORKER_INGEST = os.environ.get("WORKER_INGEST", "true").lower() in ("1", "true", "yes")
