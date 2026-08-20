# Jellyfin on k3s

Bare-metal k3s deployment of Jellyfin, pinned to the `cheeky-mini`
control-plane node (it owns the USB media store). The cluster also has a
second node, `cheeky` (GPU agent, see repo root README) — Jellyfin stays on
`cheeky-mini` regardless via the node label below, since that's where the
disk physically is.

## What this assumes about the host
- **k3s** installed with `--snapshotter=native` (required on the ZFS root);
  ServiceLB/klipper and Traefik (bundled ingress, see `platform/traefik/`)
  both left enabled. Jellyfin itself still uses its own `LoadBalancer`
  Service directly, not routed through Traefik.
- The **Seagate USB media store** mounted at `/media/cheeky/seagate_hdd` with
  `Movies/` and `TvShows/` (already in `/etc/fstab`, `uid=1000,gid=1000,nofail`).
- Intel iGPU at `/dev/dri` (`renderD128` = `render` gid **992**, `card1` =
  `video` gid **44**), advertised to the cluster as `gpu.intel.com/i915` by
  the [intel-gpu-plugin](../../platform/intel-gpu-plugin/) device plugin —
  deploy that first, Jellyfin's pod won't schedule without it.

## One-time node prep
```bash
# Pin Jellyfin to the node holding the USB media store — name it explicitly,
# now that the cluster has more than one node.
kubectl label node cheeky-mini \
  homelab/media-store=seagate node-role.homelab/media=true
```

## Deploy
```bash
kubectl apply -k jellyfin/kubernetes/
kubectl -n media rollout status deploy/jellyfin
```

## Access
```bash
kubectl -n media get svc jellyfin      # EXTERNAL-IP = node IP
# browse http://<node-ip>:8096  -> setup wizard
# add libraries: Movies -> /data/movies,  Shows -> /data/tvshows
```

## Before you edit
- **Timezone:** `20-deployment.yaml` ships `TZ=America/New_York` — change it
  to your zone if different.
- **Preserve existing config (optional):** if you want the current
  `/home/cheeky/config/jellyfin` setup, copy it into the PVC after first apply
  (the PVC path is under `/var/lib/rancher/k3s/storage/…-jellyfin-config`; find
  it with `kubectl -n media get pv`).

## Hardware transcoding
The pod requests `gpu.intel.com/i915: "1"` (the device plugin's cgroup
allow — a bare hostPath `/dev/dri` mount can't grant a non-privileged pod
`open()` on the device) and runs with supplemental groups `992` (render)
and `44` (video) for the underlying file-permission check, so no
`privileged` is needed either way. In the Jellyfin dashboard enable
**Hardware acceleration → Intel QuickSync (QSV)** (or VAAPI). Verify:
```bash
kubectl -n media exec deploy/jellyfin -- ls -l /dev/dri     # renderD128 present
intel_gpu_top                                               # engine load while transcoding
```

## Notes / limits
- **One control-plane node = pod self-healing only.** k3s restarts crashed
  pods on either node; it does **not** survive `cheeky-mini` (the only
  control-plane/etcd node) dying. True HA needs 3+ control-plane nodes.
- Media is mounted **read-only**; the USB (NTFS/ntfs-3g) is ~93% full.
- Adding another agent node (`cheeky`, the GPU box, already joined this way —
  see repo root README):
  ```bash
  curl -sfL https://get.k3s.io | K3S_URL=https://<server-ip>:6443 \
    K3S_TOKEN=$(sudo cat /var/lib/rancher/k3s/server/node-token) sh -
  ```
