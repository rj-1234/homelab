# Download automation (*arr stack)

Auto-search + download + organize into the Jellyfin library. All in the `media`
namespace, pinned to the node with the `rpool/data` dataset. Admin UIs are
**tailnet-only** (like Headlamp/Grafana).

```
Prowlarr ─(indexers)→ Radarr / Sonarr ─(release)→ qBittorrent (via gluetun VPN)
                           │                            │
                      monitors wanted            downloads /data/torrents
                           └──── hardlink/move → /data/media ────┘
                                        │
                                   Jellyfin
```

## Prerequisites (host)
```bash
# ZFS dataset — single /data root so downloads + library share a filesystem
sudo zfs create -o mountpoint=/srv/data -o compression=lz4 rpool/data
sudo mkdir -p /srv/data/torrents/{movies,tv} /srv/data/media/{movies,tv}
sudo chown -R 1000:1000 /srv/data

# ProtonVPN WireGuard secret for gluetun (key from account.protonvpn.com, enable P2P)
kubectl -n media create secret generic gluetun-vpn \
  --from-literal=VPN_SERVICE_PROVIDER=protonvpn \
  --from-literal=VPN_TYPE=wireguard \
  --from-literal=WIREGUARD_PRIVATE_KEY='<key>'
```

## Deploy
```bash
kubectl apply -f arr/kubernetes/prowlarr.yaml -f arr/kubernetes/radarr.yaml \
  -f arr/kubernetes/sonarr.yaml -f arr/kubernetes/qbittorrent.yaml
```

## Expose (tailnet-only)
Pinned ClusterIPs → `tailscale serve` per port:
```bash
sudo tailscale serve --bg --https=9696 http://10.43.200.20:9696   # Prowlarr
sudo tailscale serve --bg --https=7878 http://10.43.200.21:7878   # Radarr
sudo tailscale serve --bg --https=8989 http://10.43.200.22:8989   # Sonarr
sudo tailscale serve --bg --https=8080 http://10.43.200.23:8080   # qBittorrent
```

## Wire-up (in the UIs)
1. **qBittorrent** — get temp admin password: `kubectl -n media logs deploy/qbittorrent -c qbittorrent | grep -i password`. Set save path `/data/torrents`, categories `movies`/`tv`.
2. **Prowlarr** — add indexers; add Radarr + Sonarr under Settings → Apps (URL `http://radarr:7878`, `http://sonarr:8989`, API keys from each).
3. **Radarr/Sonarr** — Download client = qBittorrent (`http://qbittorrent:8080`). Root folder `/data/media/movies` (Radarr), `/data/media/tv` (Sonarr).
4. **Jellyfin** — add `/data/media/movies` + `/data/media/tv` as libraries.

## Notes
- gluetun kill-switch: if the VPN drops, qBittorrent egress is blocked.
- Hardlinks work because `/data/torrents` and `/data/media` are one dataset —
  imports are instant and don't double disk usage. Keep both under `/data`.
- Verify VPN IP: `kubectl -n media exec deploy/qbittorrent -c gluetun -- wget -qO- ifconfig.me`.
