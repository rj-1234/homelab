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
import shutil
import time
from datetime import date
from pathlib import Path

from . import blobs, config, db, mime

# Subdirs the scanner must never treat as uploads.
_SKIP = {".staging", ".processed", ".failed"}


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
    original_name = path.name
    # 1. claim by moving into staging (rename within the dataset = atomic).
    staged = config.STAGING / original_name
    shutil.move(str(path), str(staged))
    try:
        size = _validate(staged)
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
                    "INSERT INTO source_event(blob_sha,source,source_ref) "
                    "VALUES(%s,'upload',%s) ON CONFLICT (source,source_ref) "
                    "DO NOTHING RETURNING id",
                    (sha, f"file:{original_name}"),
                )
                if is_new:
                    cur.execute(
                        "INSERT INTO document(primary_blob_sha,title) "
                        "VALUES(%s,%s) RETURNING id",
                        (sha, original_name),
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
        shutil.move(str(staged), str(dest_dir / original_name))
        verb = "new" if is_new else "dup"
        print(f"[ingest] {verb} {original_name} sha={sha[:12]} mime={mimetype}")
    except Exception as e:  # noqa: BLE001 — quarantine, don't crash the loop
        config.FAILED.mkdir(parents=True, exist_ok=True)
        dead = config.FAILED / original_name
        shutil.move(str(staged), str(dead))
        dead.with_suffix(dead.suffix + ".error.json").write_text(
            json.dumps({"file": original_name, "error": str(e)}, indent=2)
        )
        print(f"[ingest] FAILED {original_name}: {e}")


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
