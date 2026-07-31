"""Content-addressed blob store: blobs/ab/cd/<sha256>, immutable, atomic writes."""
import hashlib
import os
from pathlib import Path

from . import config


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def blob_path(sha: str) -> Path:
    """Fan out by first two byte-pairs to keep directories small."""
    return config.BLOBS / sha[:2] / sha[2:4] / sha


def exists(sha: str) -> bool:
    return blob_path(sha).exists()


def put(src_path, sha: str) -> Path:
    """Copy src into the store at its content address. Atomic: write a temp file
    in the destination dir, fsync, then rename() into place. If the blob already
    exists, this is a no-op (immutable — same bytes, same path)."""
    dst = blob_path(sha)
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.parent / f".{sha}.tmp"
    with open(src_path, "rb") as r, open(tmp, "wb") as w:
        for chunk in iter(lambda: r.read(1024 * 1024), b""):
            w.write(chunk)
        w.flush()
        os.fsync(w.fileno())
    os.rename(tmp, dst)
    return dst
