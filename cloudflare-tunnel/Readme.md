# Installation
Cloudflare's tunnel client that runs on the client machine enabling secure tunnel connection.

## Deployment

### Docker
Fast and easy way to deploy the cloudflare client. This will pull and deploy the latest `cloudflare/cloudflared` image into a container.

> [!NOTE]  
> The tunnel connection will break if this container stops or exits for any reason and fails to auto restart.

```bash
# cd </path/to/docker-compose.yml>
docker-compose up
```

### Kubernetes 
Configurable and scalable way that deploys the image and lets it scale on multiple pods.

Source : https://github.com/cloudflare/helm-charts/tree/main

#### About
A convenient location to publish Cloudflare helm charts

#### Setup
```bash
helm repo add cloudflare https://cloudflare.github.io/helm-charts
helm repo update
```

#### Discovery
```bash
helm search repo cloudflare
```

#### Install
```bash
# cd </path/to/values.yaml>
helm install cloudflare cloudflare-tunnel-remote --values values.yaml
```
