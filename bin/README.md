# `homelab` — management CLI

One self-contained bash script wrapping the day-to-day ops for the cheeky-mini
k3s cluster. Zero dependencies (uses `kubectl` / `tailscale` / `sudo`). Run it
on the k3s node; the kubectl-only recipes also work from a remote admin machine
with a valid `KUBECONFIG`. On Windows use WSL.

## Install
```bash
ln -sf "$(pwd)/bin/homelab" ~/.local/bin/homelab   # ~/.local/bin is on PATH
homelab help
```

## Commands
```
Creds & secrets
  token [dur]          Headlamp login bearer token (default 168h)
  grafana-pw           print Grafana admin password
  set-cf-token         paste + store a new cloudflared token, restart connector
  set-grafana-pw [pw]  set/rotate Grafana password (random if omitted)
  check-secrets        verify required secrets exist

Status & URLs
  status               nodes, pods (non-Running flagged), cloudflared, tailscale
  urls                 all service URLs (public + tailnet + LAN)
  health               HTTP health-check each service

Deploy & serve
  apply [target]       kubectl apply  (jellyfin|platform|monitoring|all)
  serve                (re)establish tailscale serve: Headlamp :443, Grafana :8443
  restart <svc>        rollout restart a service
  logs <svc> [-f]      tail a service's logs

Node-join & debug
  join-cmd             print the agent-node join one-liner (server IP + token)
  debug [svc]          diagnostics bundle (+ describe/logs for <svc>)
```

`svc` = `jellyfin | homepage | headlamp | cloudflared | grafana | prometheus`

## Config (env overrides)
`KUBECONFIG` (default `/etc/rancher/k3s/k3s.yaml`), `HOMELAB_DOMAIN`,
`HOMELAB_TAILNET_HOST`, `HOMELAB_GRAFANA_TS_PORT`, `HOMELAB_HEADLAMP_IP`,
`HOMELAB_GRAFANA_IP`.

## Examples
```bash
homelab token                 # login to Headlamp
homelab grafana-pw            # Grafana admin password
homelab status               # cluster health at a glance
homelab serve                # re-add tailnet proxies after a reboot
homelab join-cmd             # command to paste on a new agent node
homelab debug jellyfin       # why is Jellyfin unhappy
```
