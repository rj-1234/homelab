# n8n — self-hosted workflow automation

[n8n](https://n8n.io), stock `docker.io/n8nio/n8n:latest` image (no custom
build — unlike [Hermes Agent](../hermes/README.md) or ContainerSSH's
auth-webhook, [Zot](../platform/zot/) isn't involved here). Own Postgres
instance, pinned to `cheeky-mini`, tailnet-only.

```
you ──https:8099──▶ n8n :5678 ──▶ postgres :5432
                        │            (workflows, credentials, execution history)
                        └──▶ N8N_ENCRYPTION_KEY Secret
                             (decrypts stored credentials — back this up)
```

## Why Postgres instead of n8n's default SQLite

n8n runs fine on its bundled SQLite for light use, but this repo already has
a settled pattern for stateful multi-workflow apps (doc-catalog, flowers):
dedicated `postgres:16` on a hostPath ZFS dataset. Following it here means
execution history doesn't degrade a single SQLite file over time, and the
DB is immediately browsable read-only through the shared
[pgweb](../platform/pgweb/) instance — no separate tooling.

## Why tailnet-only, and what that costs

Every admin service in this repo is tailnet-only by default — n8n follows
that. The real cost: n8n's most common use case is a **Webhook** trigger
node called by an external service (GitHub, Stripe, a SaaS integration).
Those can't reach a tailnet-only URL. What still works fine tailnet-only:
schedule/cron triggers, manual runs, and workflows triggered by anything
already inside the tailnet or cluster (another pod's `curl`, a script on
your own machine over Tailscale).

**If a specific integration later needs a real external webhook**, the path
is the same carve-out the [top-level README](../README.md#access-model--public-vs-private)
already documents for Flowers: a new public hostname in the Cloudflare Zero
Trust dashboard (e.g. `n8n-hooks.ch33ky.org`) routed straight to
`n8n.n8n.svc.cluster.local:5678`, **without** a Cloudflare Access policy
(third-party services can't do interactive email login) — ideally scoped to
n8n's `/webhook/*` path only if the tunnel config supports path-based
routing, so the editor UI itself stays private. Don't do this preemptively;
add it only when a concrete workflow needs it.

## Prerequisites

Host data dir on `cheeky-mini`:
```bash
sudo mkdir -p /srv/n8n/data && sudo chown 1000:1000 /srv/n8n/data
```

Secrets (never committed):
```bash
kubectl -n n8n create secret generic n8n-postgres \
  --from-literal=POSTGRES_USER=n8n \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 16)" \
  --from-literal=POSTGRES_DB=n8n
kubectl -n n8n create secret generic n8n-encryption-key \
  --from-literal=key="$(openssl rand -hex 32)"
```

**Back up the encryption key** (e.g. into `CREDENTIALS.md` via
`homelab creds`, or a password manager) before creating any real workflow
credentials. Losing it or rotating it after the fact makes every stored
credential undecryptable — n8n won't silently reset them, it'll just fail to
decrypt on next use.

## Deploy

```bash
kubectl apply -f kubernetes/00-namespace.yaml
# then the two Secret commands above
kubectl apply -k kubernetes/
kubectl -n n8n rollout status deploy/postgres
kubectl -n n8n rollout status deploy/n8n
```
Or `homelab apply n8n`.

## Expose (tailnet-only)

Pinned ClusterIP `10.43.200.57` → `tailscale serve`:
```bash
sudo tailscale serve --bg --https=8099 http://10.43.200.57:5678
```
Or `homelab serve` (re-establishes every tailnet binding in the repo).
First visit runs n8n's owner-account setup wizard.

## Notes

- `N8N_HOST`/`WEBHOOK_URL` are set to the tailnet hostname so the webhook
  URLs n8n displays in the editor are actually reachable for
  tailnet-internal callers — leaving these at their defaults would show
  `localhost` URLs that only work from inside the pod.
- `N8N_RUNNERS_ENABLED=true` opts into n8n's newer task-runner execution
  model (recommended by upstream going forward; the older in-process
  execution mode is being phased out).
- Data volume (`/home/node/.n8n`) holds n8n's local state (community-node
  installs, binary-data cache if `N8N_DEFAULT_BINARY_DATA_MODE` is ever
  changed from the default). Workflows, credentials, and execution history
  live in Postgres, not here — losing this hostPath doesn't lose workflow
  data, but does lose any manually-installed community nodes.
- Single replica, `Recreate` strategy — same reasoning as every other
  hostPath-backed app here: node-local state means no second copy can run
  elsewhere anyway.
