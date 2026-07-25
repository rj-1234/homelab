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

## Expose Headlamp to the tailnet only
Headlamp is a `ClusterIP` service (`headlamp.platform.svc:80`) with no public
route. Bridge it to the tailnet via a local port-forward + `tailscale serve`:
```bash
# keep this running (systemd unit or tmux); forwards the ClusterIP locally
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl -n platform port-forward --address 127.0.0.1 svc/headlamp 8082:80 &

sudo tailscale serve --bg --https 443 http://127.0.0.1:8082
```
Result: `https://cheeky-mini.<tailnet>.ts.net` → Headlamp, reachable only by
devices on your tailnet.

Login: paste a bearer token from the `headlamp` ServiceAccount:
```bash
kubectl -n platform create token headlamp --duration=168h
```

## Notes
- `tailscale serve status` shows active proxies; `tailscale serve --https 443 off`
  removes one.
- For a more permanent bridge than a backgrounded `kubectl port-forward`,
  consider a small systemd unit, or the Tailscale Kubernetes Operator later
  (per-service tailnet DNS, and Funnel if you ever want public TS URLs).
- Reaching Jellyfin privately: once the node is on the tailnet, it's also at
  `http://cheeky-mini.<tailnet>.ts.net:8096` via the node IP — no Cloudflare
  needed for your own devices.
