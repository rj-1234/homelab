"""Minimal structured logging: one JSON object per line on stdout.

Kubernetes captures stdout, so JSON lines stay greppable today and parse
cleanly if a log pipeline (Loki/ELK) is added later. No dependencies.

Usage:
    from . import log
    log.info("ingest.done", result="new", sha=sha[:12], src="gmail")
    log.error("job.error", job=job_id, stage=stage, error=str(e))

The first positional arg is a stable dotted event name; everything else is
structured context. Values are JSON-encoded (datetimes/paths via default=str).
"""
import json
import sys
import time


def _emit(level: str, event: str, **fields) -> None:
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "level": level,
        "event": event,
    }
    rec.update(fields)
    sys.stdout.write(json.dumps(rec, default=str) + "\n")
    sys.stdout.flush()


def info(event: str, **fields) -> None:
    _emit("info", event, **fields)


def warn(event: str, **fields) -> None:
    _emit("warn", event, **fields)


def error(event: str, **fields) -> None:
    _emit("error", event, **fields)
