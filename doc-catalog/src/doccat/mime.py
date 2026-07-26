"""MIME detection from magic bytes, never the extension (brief: sniff content).

puremagic is a pure-python wheel (no libmagic system lib) so the pods run on a
stock python:3.12-slim with no apt. It is signature-based, so files with no
magic bytes (plain text) return nothing — fall back to a utf-8 decode probe.
"""
import puremagic

_SAMPLE = 8192


def sniff(path) -> str:
    try:
        guesses = puremagic.magic_file(str(path))
    except Exception:  # noqa: BLE001 — puremagic raises on tiny/empty inputs
        guesses = []
    for g in guesses:
        if g.mime_type:
            return g.mime_type

    # No signature match: distinguish text from opaque bytes ourselves.
    with open(path, "rb") as f:
        head = f.read(_SAMPLE)
    if b"\x00" in head:
        return "application/octet-stream"
    try:
        head.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        return "application/octet-stream"
