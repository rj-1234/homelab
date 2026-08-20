# Monitoring — kube-prometheus-stack

Prometheus + Grafana + node-exporter + kube-state-metrics on k3s
(`cheeky-mini` + `cheeky`, cluster-wide — node-exporter runs as a DaemonSet
on both). Grafana is **tailnet-only** (like Headlamp); Alertmanager disabled
(dashboards only). Namespace `monitoring`.

## Install
```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Grafana admin creds (NOT committed):
kubectl create namespace monitoring
kubectl -n monitoring create secret generic grafana-admin \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="$(openssl rand -base64 18)"

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring -f values.yaml
kubectl apply -f grafana-tailnet-svc.yaml
```

## Expose Grafana (tailnet-only)
Pinned Service `grafana-tailnet` (ClusterIP `10.43.200.10`) gives `tailscale
serve` a stable target:
```bash
sudo tailscale serve --bg --https=8443 http://10.43.200.10:80
```
→ `https://cheeky-mini.tail2f4253.ts.net:8443` (login: `admin` / secret).

Reveal the password:
```bash
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d; echo
```

## Notes
- **k3s fix:** `values.yaml` disables the kubeControllerManager / kubeScheduler /
  kubeProxy / kubeEtcd scrapers — k3s binds them to localhost, so the default
  ServiceMonitors would be perpetual red targets.
- Storage on `rpool` via local-path: Prometheus 20Gi (15d retention), Grafana 5Gi.
- **Alerting** runs on Grafana's own built-in unified alerting (not
  Alertmanager, which stays off — saves a pod/RAM). Rules, the ntfy contact
  point, and the notification policy are provisioned via a sidecar-loaded
  ConfigMap, same mechanism as dashboards: see
  [alerting.yaml](alerting.yaml) (`grafana_alert: "1"` label).
- Default (stock) dashboards are disabled
  (`grafana.defaultDashboardsEnabled: false`) — only the curated
  [dashboard-overview.yaml](dashboard-overview.yaml) ships.
- Grafana admin password lives only in the `grafana-admin` Secret — if it
  ever drifts (e.g. changed via the UI, or an upgrade migration issue), the
  simplest fix is deleting the `monitoring-grafana` PVC and letting it
  reinitialize from the Secret on a fresh boot (dashboards/alerts are
  GitOps'd via the sidecar ConfigMaps, so nothing is lost — Prometheus's own
  PVC is separate and untouched).
