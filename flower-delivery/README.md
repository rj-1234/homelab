# Digital Flower Gift (flower-delivery)

A sender-composed digital flower gift. Rebuilt 2026-07-30 from a Claude
Design handoff — everything is procedural SVG (no image assets). Namespace
`flowers`, pinned to `cheeky-mini`, public at `flowers.ch33ky.org`.

## How it works

`/` is the public compose page: pick a bouquet size (5-13 stems) from 7
species (rose, ranunculus, tulip, cosmos, daffodil, chamomile, eucalyptus),
optionally pin a note to any one stem, write a message, name yourself, and
choose how long the link stays open (24h / 3 days / 7 days / 30 days). That
creates a gift and returns a share link.

`/g/:id` is the gift itself — two independent clocks:
- **Animation clock (60s, replayed every visit):** while the link is alive,
  opening it plays a bloom → full bloom → wilt → petal-fall day-cycle (dawn
  to night sky). `?dev=1` reveals a scrubber for QA.
- **Link clock (sender-chosen lifetime):** starts counting from the
  recipient's *first* open, not creation. Once it's passed, the link
  **never 404s** — it resolves permanently to a pressed-flower keepsake.

`/g/:id` is a threshold, not a loading screen: the "arrive" card requires a
tap to open, then the gift plays once per visit while alive.

## Architecture

```
web/            Vite + React + TS, public compose + gift pages
  src/engine.tsx    Species table, garden layout, SVG bloom/wilt/petal-fall
                    drawing — ported from the design handoff's Component
                    class as pure functions (not a class component) so both
                    Compose (static backdrop) and Gift (animated) can drive
                    the same drawing code independently.
  src/pages/        Compose.tsx (species picker, notes, lifetime picker),
                    Gift.tsx (arrive/gift/keepsake flow, water/wind/tap/
                    ambience interactions, dev scrubber)
admin/          Vite + React + TS + Tailwind + shadcn/ui, admin dashboard (see below)
src/flowers/    FastAPI backend — api.py (routes), db.py (psycopg3), migrate.py
migrations/     SQL migrations, applied via `python -m flowers.migrate`
kubernetes/     no-image-build k8s manifests (hostPath + Caddy), see below
```

Backend is intentionally thin: species/meaning tables and all layout math
live client-side (`web/src/engine.tsx`) since they're pure presentation —
the DB only stores what the sender actually composed.

### Schema (`migrations/001_init.sql`)
One table, `gifts`: `id` (short unguessable slug), `stems` (jsonb array of
`{species, note?}`, 1-13 entries), `message`, `sender`, `lifetime_ms`,
`created_at`, `opened_at`, `expires_at` (both null until first open).

### API (`src/flowers/api.py`)
- `GET /healthz`
- `POST /api/gifts` — creates a gift, returns `{id, url}`.
- `GET /api/gifts/:id` — stamps `opened_at`/`expires_at` on first call only;
  always returns `{stems, message, sender, expires_at, alive}`, 404 only if
  the id doesn't exist at all.
- `GET /api/admin/gifts` — every gift, newest first, with a computed
  `status` (`not_opened` / `live` / `expired`). Powers the admin dashboard.
- `DELETE /api/admin/gifts/:id` — permanently deletes a gift row; the link
  404s for any recipient immediately after. 404 if the id doesn't exist.

## Admin dashboard

KPI stat cards (total/live/not-opened/expired, animated count-up) plus a
card grid of every gift ever created (sender, message, stems+notes,
lifetime, created/opened/expires timestamps, status, copy-link, and a
delete action gated behind a confirm dialog — the link stops working and
the row is gone from Postgres immediately). Built with React + Tailwind +
shadcn/ui on its own palette (not the public site's Organic system — see
`admin/src/index.css`); GSAP drives the count-up/stagger-in motion,
respecting `prefers-reduced-motion`. Tailnet-only at
`https://cheeky-mini.tail2f4253.ts.net:8092`. Its Service ClusterIP is
pinned to `10.43.13.38`.

## Deploy (no image build, same pattern as doc-catalog)

Stock images (`python:3.12-slim`, `caddy:2-alpine`, `postgres:16`); deps
installed at pod startup via `pip --target`; source hostPath-mounted. Web/
admin builds happen on the host, then get served as static files.

```bash
kubectl apply -f kubernetes/00-namespace.yaml
kubectl -n flowers create secret generic flowers-postgres \
  --from-literal=POSTGRES_USER=flowers \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -hex 16) \
  --from-literal=POSTGRES_DB=flowers
kubectl apply -f kubernetes/10-postgres.yaml
kubectl apply -f kubernetes/30-api.yaml
kubectl -n flowers exec deploy/api -- python -m flowers.migrate

( cd web && npm install && npm run build )
( cd admin && npm install && npm run build )
kubectl apply -f kubernetes/70-admin-web.yaml -f kubernetes/75-public-web.yaml
```

Expose (host, sudo):
```bash
sudo tailscale serve --bg --https=8092 http://10.43.13.38:8080   # Flowers Admin, tailnet-only
```
Public `flowers.ch33ky.org` routing is configured in the Cloudflare Zero
Trust dashboard (outbound-only tunnel, no inbound ports — see
[cloudflare-tunnel/Readme.md](../cloudflare-tunnel/Readme.md)).

Editing `src/flowers/*` updates the pod on next restart (source is
hostPath-mounted): `kubectl -n flowers rollout restart deploy/api`. Rebuild
`web/`/`admin/` (`npm run build`) after editing either frontend.

DB browsing (read-only, tables/rows/SQL) is a shared `pgweb` instance
covering this DB and doc-catalog's — see [platform/pgweb/](../platform/pgweb/),
not something deployed per-app.

## Design system

`web/src/styles/organic.css` is a verbatim copy of the "Organic" design
system tokens from the original handoff (cream `#f5ead8`, terracotta
`#c67139`, sage `#7a8a5e`, Caprasimo + Figtree) — the public gift/compose
pages only.

`admin/` deliberately does **not** use Organic — it's shadcn/ui + Tailwind
on its own light "Analytics Dashboard" palette (`admin/src/index.css`),
sourced from the `ui-ux-pro-max` plugin's palette set rather than the
product's brand, since this is an internal tool, not customer-facing.
