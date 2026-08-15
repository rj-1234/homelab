# Hermes Agent — agent orchestrator on vLLM

[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent),
MIT. Agent orchestrator on top of [local-llm](../local-llm/README.md)'s
vLLM endpoint, WhatsApp as the primary channel. No GPU needed — runs on
`cheeky-mini`, deliberately kept off the GPU node.

No upstream image is published; this repo builds one by hand from a pinned
release tag plus one local patch, and pushes it to the self-hosted
[Zot](../platform/zot/) registry (same pattern as
[ContainerSSH's auth-webhook](../containerssh/kubernetes/README.md)).

```
gateway ──WhatsApp/Telegram (outbound only)──▶ upstream services
   │
   ├─shared pod netns (loopback)─▶ dashboard :9119  (API keys, tailnet-exposed)
   │
   └─▶ Hindsight embedded daemon (subprocess, port 8888 or 9177 — see Notes)
              ▲
              │ probes both known ports, whichever answers
       hindsight-ui :8890  (control-plane UI, tailnet-exposed)

all three containers ──▶ vllm.local-llm.svc.cluster.local:8000  (main model)
gateway/dashboard ──▶ Anthropic (opt-in, /model claude, CLAUDE_CODE_OAUTH_TOKEN)
```

- **Three containers, one pod, shared network namespace** — replaces
  upstream's docker-compose `network: host` + `depends_on` pattern:
  `dashboard` reaches `gateway` over loopback for free, no `hostNetwork: true`
  needed. `gateway` makes only outbound connections and has no Service.
- **`dashboard` holds API keys.** Upstream binds it to `127.0.0.1` and
  recommends SSH-tunnel-only access; this deploys it bound to `0.0.0.0` and
  exposed over the tailnet instead — a Service can't reach a loopback-only
  bind anyway, so keeping upstream's default would mean
  `kubectl port-forward`-only access, a real usability cost this repo
  doesn't hold anywhere else (same trust level already given to Headlamp,
  Grafana, Traefik, Zot).
- **`hindsight-ui`** bypasses Hindsight's own `hindsight-embed ui start`
  wrapper — that wrapper health-checks and, if it thinks the daemon "isn't
  running," tries to relaunch it on a profile-tracked port, which would
  collide with the real daemon already running inside `gateway`. Instead
  this container runs `@vectorize-io/hindsight-control-plane` directly with
  an explicit `--api-url`. The daemon's actual bind port isn't stable across
  restarts (confirmed live: one run bound `8888`, the default fallback; the
  next bound `9177`, its allocated profile port — a race between two
  independent writers of the same profile `.env` file), so the container
  polls both known ports on startup and connects to whichever answers,
  rather than hardcoding one.
- **Custom-provider auth can't use env-var interpolation.** Hermes's
  `custom` provider type reads `model.api_key` as a literal string from
  `config.yaml` — `${VLLM_API_KEY}`-style templating in the YAML value is
  never substituted, it gets sent to vLLM as that literal string (confirmed:
  this returned HTTP 401 the first time). Since the real key can't be
  committed to git in the ConfigMap, an `initContainer` (`render-config`)
  `sed`-substitutes the real secret values into `config.yaml` before the
  main containers start.
- **vLLM is registered as a named provider**, not the bare `provider: custom`
  shorthand — the shorthand's `base_url`/`api_key` live only inline under
  `model:`, and the dashboard's model picker overwrites that block wholesale
  on every switch, silently deleting vLLM access with no way back except
  editing the file by hand. A named `providers.vllm` entry makes it a
  persistent, selectable option instead. See
  [configmap.yaml](kubernetes/configmap.yaml) for the full block and why
  `context_length` is nested under `providers.vllm.models.<id>` specifically
  (the one path `get_custom_provider_context_length()` actually reads for
  this provider shape — every other path falls back to a 128K default that
  would silently exceed vLLM's real 65536-token window).

## Prerequisites

Zot registry deployed ([platform/zot/](../platform/zot/)) and
`cheeky-mini`'s containerd trusting it as an insecure registry (mirrors
`cheeky`'s Docker daemon config, since the image is built and pushed from
`cheeky` where Docker + Zot both live):

```bash
sudo mkdir -p /etc/rancher/k3s
printf 'mirrors:\n  "10.43.200.51:5000":\n    endpoint:\n      - "http://10.43.200.51:5000"\n' \
  | sudo tee /etc/rancher/k3s/registries.yaml
sudo systemctl restart k3s
```

Host data dir on `cheeky-mini`:
```bash
sudo mkdir -p /srv/hermes/data && sudo chown 10000:10000 /srv/hermes/data
```

## Build + push the image

No Dockerfile is vendored into this repo — built straight from upstream's
source on a pinned tag, on `cheeky` (where Docker + Zot both live):

```bash
git clone --depth 1 --branch v2026.8.3 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-agent
cd /tmp/hermes-agent
```

Apply the local Hindsight patch before building — `sync_turn()` in
`plugins/memory/hindsight/__init__.py` sends retained content as a JSON
array of `{role,content,timestamp}` turn-dicts, which Hindsight's own
chunker never reformats into prose before handing it to the extraction LLM.
Small local models pattern-match the raw JSON instead of extracting facts
from it, so fact extraction silently returns 0 facts on every message. Patch
it to send plain `"User: ...\nAssistant: ..."` text instead — see memory
`hermes_hindsight_memory_provider` for the full root-cause trace and diff.
Re-apply (or `git diff` forward) on any future tag bump; it doesn't exist
upstream.

```bash
docker build -t 10.43.200.51:5000/hermes-agent:v2026.8.3-local.1 .
docker push 10.43.200.51:5000/hermes-agent:v2026.8.3-local.1
docker run --rm 10.43.200.51:5000/hermes-agent:v2026.8.3-local.1 id hermes   # confirm UID/GID matches 10-hermes.yaml's 10000:10000
```

Tag suffixed `-local.N` rather than reusing the upstream tag so
`imagePullPolicy: IfNotPresent` (the default, unset in `10-hermes.yaml`)
can't silently keep serving stale cached layers after a patch — bump the
suffix on every rebuild.

## Deploy

```bash
kubectl apply -f kubernetes/00-namespace.yaml
kubectl -n hermes create secret generic vllm-api-key \
  --from-literal=key="$(kubectl -n local-llm get secret vllm-api-key -o jsonpath='{.data.key}' | base64 -d)"
kubectl -n hermes create secret generic hermes-dashboard-auth \
  --from-literal=password_hash='<output of hash_password(), see upstream docs>'
kubectl -n hermes create secret generic anthropic-oauth-token \
  --from-literal=token='<output of `claude setup-token`, needs Claude Pro/Max login>'
kubectl apply -k kubernetes/
```

Claude subscription models (opt-in — `/model claude` in a session, vLLM
stays the default main model): the `anthropic-oauth-token` secret carries
the `CLAUDE_CODE_OAUTH_TOKEN` Hermes's built-in `anthropic` provider reads
directly — no separate Anthropic API billing needed.

WhatsApp pairing (one-time, scan the printed QR):
```bash
kubectl -n hermes exec -it deploy/hermes -c gateway -- hermes whatsapp
```

## Expose (tailnet-only)

Pinned ClusterIPs (`10.43.200.53` dashboard, `10.43.200.54` Hindsight UI) →
`tailscale serve`:
```bash
sudo tailscale serve --bg --https=8096 http://10.43.200.53:9119   # Hermes dashboard
sudo tailscale serve --bg --https=8097 http://10.43.200.54:8890   # Hindsight control-plane UI
```
Or just `homelab serve` (re-establishes every tailnet binding in the repo).

## Notes

- Hindsight's tuning env vars (`HINDSIGHT_API_RETAIN_MAX_COMPLETION_TOKENS`,
  the `HINDSIGHT_API_CONSOLIDATION_*` block in `10-hermes.yaml`) exist
  because Hindsight's defaults are sized for big cloud models — retain
  defaults to requesting 64000 output tokens, which leaves ~1536 tokens of
  vLLM's 65536-token window for input, so every retain times out regardless
  of content length. Values here follow the small-local-model
  recommendations from vectorize-io/hindsight discussion #2199.
- `hindsight-ui`'s `NPM_CONFIG_MIN_RELEASE_AGE=0` override is scoped to that
  one container's `npx` install — the image ships a supply-chain-security
  default (`min-release-age=14`) that rejected `hindsight-control-plane`'s
  `nanoid` dependency, not in Hermes's own allowlist. Control-plane version
  is pinned to `0.8.6` to match the installed `hindsight_embed` (its own
  code defaults to its own `__version__` "so the stack stays in lockstep");
  `@latest` (0.9.0) fails outright on an unresolvable `nanoid` range.
- Claude is wired as an opt-in `/model claude` alias rather than replacing
  vLLM as the default — vLLM stays free/local for routine traffic, Claude is
  there for sessions that specifically need it.
