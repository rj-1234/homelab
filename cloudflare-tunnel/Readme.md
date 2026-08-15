# Cloudflare Tunnel

Outbound-only connector exposing selected services on the public domain
(`home.ch33ky.org`, `jellyfin.ch33ky.org`, `flowers.ch33ky.org`) without
opening any inbound ports. Runs in k3s as a Deployment; the tunnel is
**remotely managed** — hostname → service routing lives in the Cloudflare
Zero Trust dashboard.

## Deploy

1. Create the tunnel in Cloudflare Zero Trust → Networks → Tunnels (type
   `Cloudflared`), copy its connector **token**.
2. Store the token as a k8s Secret (never committed):
   ```bash
   kubectl -n platform create secret generic cloudflared-token \
     --from-literal=token='<TOKEN>'
   ```
3. Apply the connector:
   ```bash
   kubectl apply -f kubernetes/cloudflared-deployment.yaml
   kubectl -n platform rollout status deploy/cloudflared
   ```
   Connector shows **HEALTHY** in the dashboard.

## Routing (dashboard → tunnel → Public Hostnames)

| Hostname | Service | Auth |
|---|---|---|
| `home.ch33ky.org` | `http://homepage.platform.svc.cluster.local:3000` | Cloudflare Access (email) |
| `jellyfin.ch33ky.org` | `http://jellyfin.media.svc.cluster.local:8096` | Jellyfin's own login |
| `flowers.ch33ky.org` | `http://public-web.flowers.svc.cluster.local:8080` | none — public/link-based by design |

Type is **HTTP** (pods serve plain HTTP). Protect `home` with an Access policy;
leave `jellyfin` on its own auth so native apps work; leave `flowers` with no
auth at all — anyone with a gift link can open it, nothing sensitive is
stored.

> Secrets never live in the repo. `kubernetes/values.yaml` is gitignored;
> `values.example.yaml` is the template for the optional helm-chart path.
