# Jellyfin on k3s

Bare-metal k3s deployment of Jellyfin for the `cheeky-mini` homelab node.
Single node today, built to stay put when agent nodes join later.

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
# Pin Jellyfin to the node holding the USB media store.
kubectl label node "$(kubectl get nodes -o name | head -1 | cut -d/ -f2)" \
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
- **Single node = pod self-healing only.** k3s restarts crashed pods; it does
  **not** survive the box dying. True HA needs 3+ control-plane nodes.
- Media is mounted **read-only**; the USB (NTFS/ntfs-3g) is ~93% full.
- Adding an agent node later:
  ```bash
  curl -sfL https://get.k3s.io | K3S_URL=https://<server-ip>:6443 \
    K3S_TOKEN=$(sudo cat /var/lib/rancher/k3s/server/node-token) sh -
  ```
