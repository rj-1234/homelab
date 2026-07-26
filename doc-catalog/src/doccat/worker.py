"""Ingest worker: reconcile-scan the inbox every SCAN_INTERVAL seconds.

The 30s scan is the source of truth. inotify (latency optimization) is a later
add-on — if it breaks we lose responsiveness, not data.
"""
import time

from . import config, ingest, jobs


def main() -> None:
    for d in (config.STAGING, config.PROCESSED, config.FAILED, config.BLOBS):
        d.mkdir(parents=True, exist_ok=True)
    print(f"[worker] watching {config.INBOX} every {config.SCAN_INTERVAL}s")
    seen: dict = {}
    while True:
        try:
            ingest.scan_once(seen)   # ingest new uploads
            jobs.drain()             # run pending pipeline jobs (text extraction)
        except Exception as e:  # noqa: BLE001 — never let the loop die
            print(f"[worker] loop error: {e}")
        time.sleep(config.SCAN_INTERVAL)


if __name__ == "__main__":
    main()
