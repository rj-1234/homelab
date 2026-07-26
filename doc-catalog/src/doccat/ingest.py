"""Ingest transaction + reconcile scan with a quiescence guard.

Ingest order (crash-safety matters):
  1. move (not copy) into inbox/.staging/
  2. sniff MIME from magic bytes
  3. sha256 the raw bytes
  4. write blob first (temp -> atomic rename), THEN the DB rows
  5. always insert source_event (provenance, even on a known hash)
  6. enqueue a job only if the blob is new
  7. move original to inbox/.processed/<date>/; failures to .failed/ + sidecar
"""
import json
import re
import shutil
import time
import uuid
from datetime import date
from pathlib import Path

from . import blobs, config, db, log, mime

# Subdirs the scanner must never treat as uploads.
_SKIP = {".staging", ".processed", ".failed"}
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(name: str) -> str:
    base = Path((name or "").strip()).name or "attachment"
    return (_SAFE.sub("_", base).lstrip(".") or "attachment")[-180:]


class Reject(Exception):
    """A file we refuse to ingest (zero-byte, oversize, ...)."""


def _candidates():
    """Loose files directly in the inbox (not the dot-dirs, not subdirs)."""
    for p in config.INBOX.iterdir():
        if p.name in _SKIP or p.name.startswith("."):
            continue
        if p.is_file():
            yield p


def _validate(path: Path) -> int:
    size = path.stat().st_size
    if size == 0:
        raise Reject("zero-byte file")
    if size > config.MAX_BYTES:
        raise Reject(f"oversize: {size} > {config.MAX_BYTES}")
    return size


def ingest_one(path: Path) -> None:
    """A loose upload file sitting in the inbox."""
    staged = config.STAGING / path.name
    shutil.move(str(path), str(staged))        # atomic rename within the dataset
    _ingest_staged(staged, path.name, path.name,
                   {"source": "upload", "source_ref": f"file:{path.name}"})


def ingest_bytes(data: bytes, filename: str, prov: dict) -> None:
    """Ingest in-memory bytes (e.g. a Gmail attachment) with given provenance.
    prov: source, source_ref (unique), and optional sender/subject/received_at/title."""
    config.STAGING.mkdir(parents=True, exist_ok=True)
    safe = _safe_name(filename)
    staged = config.STAGING / f"{uuid.uuid4().hex}-{safe}"   # unique, no collisions
    staged.write_bytes(data)
    _ingest_staged(staged, safe, prov.get("title") or safe, prov)


def _ingest_staged(staged: Path, original_name: str, title: str, prov: dict) -> None:
    """Shared core: validate -> sniff -> sha -> blob-first -> DB rows -> archive.
    Records provenance for every arrival; creates a document + job only for a
    genuinely new blob. Any failure quarantines the staged file, never crashes."""
    try:
        size = _validate(staged)               # 1
        mimetype = mime.sniff(staged)          # 2
        sha = blobs.sha256_file(staged)        # 3
        is_new = not blobs.exists(sha)
        blobs.put(staged, sha)                 # 4 (blob before DB rows)

        conn = db.connect()
        with conn:
            with conn.cursor() as cur:
                if is_new:
                    cur.execute(
                        "INSERT INTO blob(sha256,size,mime,path) VALUES(%s,%s,%s,%s)"
                        " ON CONFLICT (sha256) DO NOTHING",
                        (sha, size, mimetype, str(blobs.blob_path(sha))),
                    )
                # 5. always record provenance; dedupe on (source, source_ref).
                cur.execute(
                    "INSERT INTO source_event"
                    "(blob_sha,source,source_ref,sender,subject,received_at) "
                    "VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT (source,source_ref) "
                    "DO NOTHING",
                    (sha, prov["source"], prov["source_ref"], prov.get("sender"),
                     prov.get("subject"), prov.get("received_at")),
                )
                if is_new:
                    cur.execute(
                        "INSERT INTO document(primary_blob_sha,title) "
                        "VALUES(%s,%s) RETURNING id",
                        (sha, title),
                    )
                    doc_id = cur.fetchone()[0]
                    # 6. enqueue downstream work only for genuinely new content.
                    cur.execute(
                        "INSERT INTO job(document_id,stage) VALUES(%s,'text')",
                        (doc_id,),
                    )
        # 7. archive the processed original.
        dest_dir = config.PROCESSED / date.today().isoformat()
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged), str(dest_dir / staged.name))
        log.info("ingest.done", result=("new" if is_new else "dup"),
                 name=original_name, sha=sha[:12], mime=mimetype,
                 src=prov["source"])
    except Exception as e:  # noqa: BLE001 — quarantine, don't crash the loop
        config.FAILED.mkdir(parents=True, exist_ok=True)
        dead = config.FAILED / staged.name
        shutil.move(str(staged), str(dead))
        dead.with_suffix(dead.suffix + ".error.json").write_text(
            json.dumps({"file": original_name, "error": str(e)}, indent=2)
        )
        log.error("ingest.failed", name=original_name, error=str(e))


def scan_once(seen: dict) -> None:
    """One reconcile pass. `seen` carries (size,mtime) across calls so a file is
    only claimed once stable across two scans and old enough (quiescence)."""
    now = time.time()
    current = {}
    for p in _candidates():
        try:
            st = p.stat()
        except FileNotFoundError:
            continue
        sig = (st.st_size, st.st_mtime)
        current[p] = sig
        stable = seen.get(p) == sig
        old_enough = (now - st.st_mtime) >= config.QUIESCENCE_AGE
        if stable and old_enough:
            ingest_one(p)
            current.pop(p, None)
    seen.clear()
    seen.update(current)
