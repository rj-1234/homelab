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
OCR_DPI = int(os.environ.get("OCR_DPI", "150"))          # pdf page raster DPI (memory vs. accuracy)
OCR_CONF_THRESHOLD = float(os.environ.get("OCR_CONF_THRESHOLD", "0.6"))
CLAUDE_VISION_MODEL = os.environ.get("CLAUDE_VISION_MODEL", "claude-opus-5")

# --- Gmail ingestion --------------------------------------------------------
# Each account is a google "authorized_user" token JSON (client id/secret +
# refresh token, gmail.readonly scope), mounted read-only as token-<label>.json.
# Accounts are discovered from the files — no manual seeding.
GMAIL_TOKENS_DIR = Path(os.environ.get("GMAIL_TOKENS_DIR", "/secrets/gmail"))
GMAIL_POLL_INTERVAL = int(os.environ.get("GMAIL_POLL_INTERVAL", "300"))   # 5 min
# Extra backfill filter, prepended to the auto-built `has:attachment
# (filename:...)` clause. Empty by default: this is a personal archive, so
# backfill spans the whole mailbox (docs from 2016+). A `newer_than:` bound here
# silently drops everything older — the original cause of "old docs never synced".
GMAIL_INITIAL_QUERY = os.environ.get("GMAIL_INITIAL_QUERY", "")
# Optional minimum attachment size. Default 0 (off): the docs-only MIME/extension
# allowlist already excludes newsletter images, and a floor here just discards
# legitimate small PDFs (receipts, short letters).
GMAIL_MIN_ATTACH_BYTES = int(os.environ.get("GMAIL_MIN_ATTACH_BYTES", "0"))

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
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
    "application/vnd.ms-powerpoint,"
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
).split(",")))
GMAIL_ATTACH_EXT = tuple(filter(None, os.environ.get(
    "GMAIL_ATTACH_EXT", ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx").split(",")))

# Also ingest image attachments (phone photos / scans of documents: passport,
# visa, signed forms). Gated by the same sender allow/deny rules, plus a size
# floor below — real document photos are >100KB, while email-signature logos and
# tracking pixels are tiny, so the floor keeps those out without a sender rule.
GMAIL_IMAGE_MIME = set(filter(None, os.environ.get(
    "GMAIL_IMAGE_MIME",
    "image/jpeg,image/png,image/heic,image/heif,image/webp,image/tiff",
).split(",")))
GMAIL_IMAGE_EXT = tuple(filter(None, os.environ.get(
    "GMAIL_IMAGE_EXT", ".jpg,.jpeg,.png,.heic,.heif,.webp,.tif,.tiff").split(",")))
# Minimum size for an image attachment (bytes). Documents have no floor (small
# PDFs are valid); images do, to drop logos/signatures/tracking pixels.
GMAIL_IMAGE_MIN_BYTES = int(os.environ.get("GMAIL_IMAGE_MIN_BYTES", str(100 * 1024)))

# --- Embedding + semantic tagging (Phase 7) ---------------------------------
# bge-base-en-v1.5 (768-dim, 512-token, standard BERT — no custom Hub code)
# hosted in a dedicated CPU pod. Chosen over Qwen3-0.6B because the 512-token cap
# negates Qwen's long-context/size edge; this is ~4-5x lighter for near-equal
# accuracy. (gte-base-en-v1.5's trust_remote_code path crashed on CPU inference.)
EMBEDDER_URL = os.environ.get("EMBEDDER_URL", "http://embedder:8000")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-base-en-v1.5")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "768"))
# Cap the doc text sent for the doc-level vector (chars). 32k ctx handles it,
# but keep a sane bound. Pages are embedded separately as chunks.
EMBED_MAX_CHARS = int(os.environ.get("EMBED_MAX_CHARS", "2500"))
# Top-level category assignment (multi-label) is relative, not a fixed cutoff:
# bge-base cosines are compressed into a narrow band (~0.45-0.67) where an
# absolute floor tags everything. A category is assigned if its score is within
# CLASSIFY_MARGIN of the document's top category AND above CLASSIFY_THRESHOLD
# (a sanity floor). The margin adapts per-doc: a document that sits strongly in
# one category gets only that; one spanning a few gets the top cluster.
CLASSIFY_THRESHOLD = float(os.environ.get("CLASSIFY_THRESHOLD", "0.35"))
CLASSIFY_MARGIN = float(os.environ.get("CLASSIFY_MARGIN", "0.03"))
# Once a category has at least this many user-confirmed documents, its prototype
# switches from the zero-shot description to the centroid of those documents'
# vectors — accuracy that improves as you correct tags, no LLM.
CLASSIFY_MIN_CENTROID = int(os.environ.get("CLASSIFY_MIN_CENTROID", "2"))
# Embed each page as its own chunk (for page-level semantic search). Off by
# default: the doc-level vector alone drives tagging, and per-page embedding is
# the slow part on CPU (a 9-page doc = 10 encodes). Enable once search is wired.
EMBED_PAGES = os.environ.get("EMBED_PAGES", "false").lower() in ("1", "true", "yes")

# --- Field vault / PII extraction (Phase 8) ---------------------------------
# Presidio analyzer (spaCy NER + pattern recognizers + validators) hosted in a
# dedicated on-node pod. The `fields` stage calls it with a document's text and
# stores the returned spans as candidate vault fields (unconfirmed). Local only —
# no PII egress. See recognizers.py for the corpus-tuned custom patterns.
PRESIDIO_URL = os.environ.get("PRESIDIO_URL", "http://presidio:8000")
# Minimum extractor confidence to keep a candidate. Context-gated recognizers sit
# low on their own and get a context boost near the right words; 0.4 keeps the
# structured hits (USCIS receipt, SSN, card) and drops bare digit-run noise.
FIELDS_SCORE_THRESHOLD = float(os.environ.get("FIELDS_SCORE_THRESHOLD", "0.4"))

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
# A job left 'running' longer than this (its worker died mid-job) is reclaimed to
# 'pending' by reconcile(). Set above the slowest expected stage runtime.
JOB_STALE_SECONDS = int(os.environ.get("JOB_STALE_SECONDS", "900"))  # 15 min
