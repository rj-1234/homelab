# qBittorrent

Standalone torrent client behind a VPN kill-switch (gluetun). No indexer or
auto-organize automation — add torrents manually. In the `media` namespace,
pinned to the node with the `rpool/data` dataset. Admin UI is
**tailnet-only** (like Headlamp/Grafana).

```
qBittorrent (via gluetun VPN) → downloads /data/torrents → move/hardlink → /data/media → Jellyfin
```

Prowlarr/Radarr/Sonarr (indexer search + automated fetch/organize) were
dropped as unneeded.

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
kubectl apply -f arr/kubernetes/qbittorrent.yaml
```

## Expose (tailnet-only)
Pinned ClusterIP → `tailscale serve`:
```bash
sudo tailscale serve --bg --https=8080 http://10.43.200.23:8080   # qBittorrent
```

## Wire-up
1. Get temp admin password: `kubectl -n media logs deploy/qbittorrent -c qbittorrent | grep -i password`.
2. Set save path `/data/torrents`, categories `movies`/`tv`.
3. Add torrents/magnets manually (no indexer integration).
4. After a download finishes, move/hardlink it into `/data/media/movies` or `/data/media/tv` and rescan the corresponding Jellyfin library.
5. ProtonVPN's NAT-PMP forwarded port is dynamic, not the static `6881`
   qBittorrent defaults to — read it and set it manually:
   `kubectl -n media exec deploy/qbittorrent -c gluetun -- cat /tmp/gluetun/forwarded_port`,
   then WebUI → Options → Connection → set that port, disable qBittorrent's
   own UPnP/NAT-PMP (gluetun already handles forwarding).

## Notes
- gluetun kill-switch: if the VPN drops, qBittorrent egress is blocked.
- Hardlinks work because `/data/torrents` and `/data/media` are one dataset —
  imports are instant and don't double disk usage. Keep both under `/data`.
- Verify VPN IP: `kubectl -n media exec deploy/qbittorrent -c gluetun -- wget -qO- ifconfig.me`.
