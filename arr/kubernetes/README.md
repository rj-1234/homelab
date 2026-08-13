# Download automation (*arr stack)

Auto-search + download + organize into the Jellyfin library. All in the
`media` namespace, pinned to the node with the `rpool/data` dataset. Admin
UIs are **tailnet-only** (like Headlamp/Grafana). qBittorrent rides a
gluetun (ProtonVPN WireGuard) kill-switch; Prowlarr/Radarr/Sonarr don't need
the VPN (indexer/API traffic, not torrent traffic).

```
Prowlarr ─(indexers)→ Radarr / Sonarr ─(release)→ qBittorrent (via gluetun VPN)
                           │                            │
                      monitors wanted        downloads straight into
                           └──────────→ /data/media/{movies,tv} ←──────┘
                                        │
                                   Jellyfin (library volume, same path)
```

Downloads land directly in the Jellyfin library path — no manual
move/hardlink step. qBittorrent's categories and Radarr/Sonarr's root
folders are both set to `/data/media/movies` / `/data/media/tv`, which is
the same `/srv/data/media` hostPath Jellyfin's `library` volume already
watches ([jellyfin/kubernetes/20-deployment.yaml](../../jellyfin/kubernetes/20-deployment.yaml)).

## Prerequisites (host)
```bash
# ZFS dataset — single /data root so downloads + library share a filesystem
sudo zfs create -o mountpoint=/srv/data -o compression=lz4 rpool/data
sudo mkdir -p /srv/data/media/{movies,tv}
sudo chown -R 1000:1000 /srv/data

# ProtonVPN WireGuard secret for gluetun (key from account.protonvpn.com, enable P2P)
kubectl -n media create secret generic gluetun-vpn \
  --from-literal=VPN_SERVICE_PROVIDER=protonvpn \
  --from-literal=VPN_TYPE=wireguard \
  --from-literal=WIREGUARD_PRIVATE_KEY='<key>'
```

## Deploy
```bash
kubectl apply -f arr/kubernetes/qbittorrent.yaml -f arr/kubernetes/prowlarr.yaml \
  -f arr/kubernetes/radarr.yaml -f arr/kubernetes/sonarr.yaml
```

## Expose (tailnet-only)
Pinned ClusterIPs → `tailscale serve` per port:
```bash
sudo tailscale serve --bg --https=8080 http://10.43.200.23:8080   # qBittorrent
sudo tailscale serve --bg --https=9696 http://10.43.200.20:9696   # Prowlarr
sudo tailscale serve --bg --https=7878 http://10.43.200.21:7878   # Radarr
sudo tailscale serve --bg --https=8989 http://10.43.200.22:8989   # Sonarr
```

## Wire-up
1. **qBittorrent** — WebUI login is set (not the linuxserver temp-password
   flow — creds live in `platform/homepage/configmap.yaml`'s
   `HOMEPAGE_VAR_QBIT_PW` reference / your own notes). Categories
   `movies`/`tv` → save path `/data/media/movies` / `/data/media/tv`.
2. **Prowlarr** — add indexers under Indexers. Then Settings → Apps → add:
   - Radarr: `http://radarr.media.svc.cluster.local:7878` + its API key
     (Radarr → Settings → General)
   - Sonarr: `http://sonarr.media.svc.cluster.local:8989` + its API key
     (Sonarr → Settings → General)
3. **Radarr/Sonarr** — Settings → Download Clients → add qBittorrent
   (`http://qbittorrent.media.svc.cluster.local:8080`, WebUI creds). Root
   folder: `/data/media/movies` (Radarr), `/data/media/tv` (Sonarr).
4. **Jellyfin** — `library` volume already mounts `/srv/data/media`; after
   the first import, trigger one manual library scan. Optional follow-up:
   point Radarr/Sonarr's "Jellyfin/Emby" notification connection at Jellyfin
   to auto-trigger scans on import instead.
5. ProtonVPN's NAT-PMP forwarded port is dynamic, not the static `6881`
   qBittorrent defaults to — read it and set it manually:
   `kubectl -n media exec deploy/qbittorrent -c gluetun -- cat /tmp/gluetun/forwarded_port`,
   then WebUI → Options → Connection → set that port, disable qBittorrent's
   own UPnP/NAT-PMP (gluetun already handles forwarding).

## Notes
- gluetun kill-switch: if the VPN drops, qBittorrent egress is blocked.
  Prowlarr/Radarr/Sonarr aren't behind it — only torrent transfer traffic
  needs the tunnel.
- Search plugins built into qBittorrent itself weren't used — Prowlarr is
  the actual search layer (maintained indexer definitions; client-side
  scraper plugins rot as tracker sites change).
- Verify VPN IP: `kubectl -n media exec deploy/qbittorrent -c gluetun -- wget -qO- ifconfig.me`.
