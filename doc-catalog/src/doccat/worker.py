"""Ingest worker: reconcile-scan the inbox every SCAN_INTERVAL seconds.

The 30s scan is the source of truth. inotify (latency optimization) is a later
add-on — if it breaks we lose responsiveness, not data.
"""
import time

from . import config, gmail, ingest, jobs, log


def main() -> None:
    stages = config.WORKER_STAGES
    if config.WORKER_INGEST:
        for d in (config.STAGING, config.PROCESSED, config.FAILED, config.BLOBS):
            d.mkdir(parents=True, exist_ok=True)
    log.info("worker.start", stages=list(stages), ingest=config.WORKER_INGEST,
             scan_interval=config.SCAN_INTERVAL)
    seen: dict = {}
    last_gmail = 0.0
    while True:
        try:
            if config.WORKER_INGEST:
                ingest.scan_once(seen)   # ingest new uploads
                now = time.monotonic()
                if now - last_gmail >= config.GMAIL_POLL_INTERVAL:
                    gmail.poll()         # pull Gmail attachments into the pipeline
                    last_gmail = now
            jobs.reconcile(stages)       # requeue retryable failed jobs (backoff)
            jobs.drain(stages)           # run pending pipeline jobs for our stages
        except Exception as e:  # noqa: BLE001 — never let the loop die
            log.error("worker.loop_error", error=str(e))
        time.sleep(config.SCAN_INTERVAL)


if __name__ == "__main__":
    main()
