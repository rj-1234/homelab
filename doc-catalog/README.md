# Document Catalog

Personal document cataloging on the `cheeky-mini` k3s homelab. Ingest docs from
web/phone upload + Gmail, OCR + LLM-extract, dedupe, and make the corpus
searchable. Single user, <5k docs — built for quality and simplicity, not scale.

**Everything is Postgres + files on the NVMe.** No object store, no message
broker. Queue = Postgres `SELECT … FOR UPDATE SKIP LOCKED`. Blobs =
content-addressed files. Search = `tsvector` + `pgvector` in the same DB.

## Core principles
1. Originals are immutable; everything else is derived and regenerable.
2. Idempotent, content-hash-keyed pipeline — re-running the corpus is safe/cheap.
3. Renditions are byte-deterministic.
4. Never merge/delete duplicates destructively — link, pick canonical, hide rest.
5. Blast radius: financial/medical index → Tailscale-only, encrypted at rest,
   real 3-2-1 backup with Postgres WAL archiving.

## Storage (rpool/docs ZFS dataset → /srv/docs)
```
inbox/                writable, watched, transient   (FileBrowser points here)
inbox/.staging/  .processed/  .failed/
blobs/ab/cd/<sha256>  content-addressed, immutable
library/              read-only symlink tree, generated from DB
pg/                   Postgres PGDATA
```

## Pipeline
`ingest → dedupe → normalize → triage → OCR → extract → index → review`

Extraction backend = **Claude API** (see `doc-catalog-extract-backend` memory).
Gmail ingest = raw Gmail API headless poller (tokens in `~/.config/doc-catalog/`).

## Build order (each phase independently useful)
1. **Ingest + exact dedupe + list view** ← current
2. Job runner + text-layer extraction
3. Postgres FTS + browse/filter UI
4. OCR path + HEIC/image normalization
5. Gmail ingest (label + allowlist + candidate queue)
6. LLM classification + typed extraction + review; near/logical dedup
7. Embeddings + hybrid retrieval; chat-over-docs

## Phase 1 — run it

### 1. Dataset (once, sudo)
```bash
sudo zfs create rpool/docs
sudo mkdir -p /srv/docs/{inbox/.staging,inbox/.processed,inbox/.failed,blobs,library,pg}
sudo chown -R 1000:1000 /srv/docs && chmod 2775 /srv/docs/inbox
```

### 2. Postgres on k3s
```bash
kubectl apply -f kubernetes/00-namespace.yaml
kubectl -n docs create secret generic doccat-postgres \
  --from-literal=POSTGRES_USER=doccat \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -hex 16) \
  --from-literal=POSTGRES_DB=doccat
kubectl apply -f kubernetes/10-postgres.yaml
```

### 3. Local dev loop (worker + API against the cluster DB)
```bash
uv sync
kubectl -n docs port-forward svc/postgres 5432:5432 &   # DB reachable at localhost
export DATABASE_URL='postgresql://doccat:<pw>@localhost:5432/doccat'
export DOCS_ROOT=/srv/docs
uv run doccat-migrate                       # apply schema
uv run doccat-worker &                      # watch inbox
uv run uvicorn doccat.api:app --port 8000   # list view at http://localhost:8000
```
Drop a file into `/srv/docs/inbox/` → within ~30s it appears in the list; a
second copy of the same bytes adds a `source_event` but no new document (exact
dedupe). Failures land in `inbox/.failed/` with a `.error.json` sidecar.

## Phase 1 — deploy on k3s (no image build)

Pods use stock `python:3.12-slim` from docker.io; an initContainer pip-installs
deps into an emptyDir and the app source is hostPath-mounted from this repo.
No registry, no Dockerfile. Pinned to `cheeky-mini` (repo + dataset live here).

```bash
mkdir -p /srv/docs/.filebrowser
kubectl apply -f kubernetes/20-worker.yaml \
               -f kubernetes/30-api.yaml \
               -f kubernetes/40-filebrowser.yaml
kubectl -n docs get pods
```

Expose tailnet-only (host, sudo — no public ingress per principle #5):
```bash
sudo tailscale serve --bg --https=8090 http://10.43.200.31:8080   # FileBrowser (upload)
sudo tailscale serve --bg --https=8091 http://10.43.200.30:8000   # catalog list view
```
FileBrowser first login is `admin`/`admin` — **change it immediately**. Install
it as a phone PWA (Add to Home Screen) for upload-anywhere ingestion.

> Editing `src/doccat/*` updates the pods on their next restart (source is
> hostPath-mounted): `kubectl -n docs rollout restart deploy/worker deploy/api`.
> Deps change → the initContainer reinstalls on restart automatically.
