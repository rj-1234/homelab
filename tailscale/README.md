# Tailscale — private access + SSH

Host install (not a k8s workload). Gives `cheeky-mini` a tailnet identity so you
can reach admin services and SSH the box from anywhere, without exposing them
publicly. This is the **private** half of the access design; Cloudflare Tunnel
is the public half.

## Install (system package — run with sudo)
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
```
- Approve the node in the Tailscale admin console.
- Enable **MagicDNS** and **HTTPS certificates** (admin console → DNS) — required
  for `tailscale serve` to hand out a `*.ts.net` HTTPS name.

## Expose an admin service to the tailnet only
No `kubectl port-forward` needed — a k3s ClusterIP is already reachable from
the host's own network namespace (kube-proxy sets that up), so
`tailscale serve` can point straight at one. Every admin service in this
repo gets a **pinned ClusterIP** (set in its Service manifest) so the target
IP survives pod/Service redeploys, then a host-level `tailscale serve`
binding:
```bash
sudo tailscale serve --bg --https=443 http://10.43.142.241:80   # Headlamp, pinned ClusterIP
```
Result: `https://cheeky-mini.<tailnet>.ts.net` → Headlamp, reachable only by
devices on your tailnet. Same pattern for every other tailnet-only service
in the repo (Grafana, pgweb, Field Vault, Flowers Admin, Traefik dashboard,
Open WebUI, Zot, Hermes dashboard, Hindsight UI, the arr stack,
ContainerSSH/Wetty) — each just a different pinned ClusterIP + port. Rather
than running each `tailscale serve` command by hand, `homelab serve`
(re-)establishes all of them in one shot, and `homelab urls` prints the
resulting list.

Login: paste a bearer token from the `headlamp` ServiceAccount:
```bash
kubectl -n platform create token headlamp --duration=168h
```

## Notes
- `tailscale serve status` shows active proxies; `tailscale serve --https=443 off`
  removes one.
- A future upgrade path worth considering: the Tailscale Kubernetes Operator
  (per-service tailnet DNS, and Funnel if you ever want a public TS URL)
  instead of manually pinning ClusterIPs + host-level `tailscale serve`.
- Reaching Jellyfin privately: once the node is on the tailnet, it's also at
  `http://cheeky-mini.<tailnet>.ts.net:8096` via the node IP — no Cloudflare
  needed for your own devices.
