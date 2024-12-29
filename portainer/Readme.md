# Installation
Portainer installation.

## Deployment

### Docker

```bash
# cd </path/to/docker-compose.yml>
docker-compose up
```

### Kubernetes 
TODO: add the helm installation steps

portainer comes as an addon from community in `microk8s` installation, to enable the portainer deployment:

```bash
# enable coimmunity addons
sudo microk8s enable community

# deploy portainer
sudo microk8s enable portainer
```