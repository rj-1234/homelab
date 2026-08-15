# local-llm — vLLM + Open WebUI

Self-hosted OpenAI-compatible inference on `cheeky`'s RTX 3080. Backs
[Open WebUI](#open-webui) (manual chat testing) and
[Hermes Agent](../hermes/README.md) (the actual agent orchestrator).
**Cluster-internal only — vLLM itself is never tailnet or public exposed**;
Open WebUI and Hermes are the only things that talk to it.

## vLLM

`kubernetes/10-vllm.yaml`, pinned to `cheeky` (`nodeSelector:
kubernetes.io/hostname: cheeky`), `nvidia.com/gpu: 1` (via
[nvidia-gpu-plugin](../platform/nvidia-gpu-plugin/)). ClusterIP pinned
`10.43.200.50:8000`. Auth via the `vllm-api-key` Secret.

Model/quant/context-length/tool-parser are all env vars on the Deployment
(not baked into the command), so swapping models is `kubectl set env` +
`kubectl rollout restart`, not a manifest edit:

| Env var | Current value | Why |
|---|---|---|
| `MODEL_ID` | `casperhansen/llama-3.2-3b-instruct-awq` | Landed here after a model-selection history (Qwen2.5-7B → static-YaRN context extension attempt → Gemma 4 E4B → Llama-3.1-8B, all rejected first — see `10-vllm.yaml`'s inline comments and the `SERVED_MODEL_NAME` note below). |
| `QUANTIZATION` | `awq` | 4-bit, fits the 3080's usable VRAM alongside KV-cache. |
| `MAX_MODEL_LEN` | `65536` | Genuinely native for this model (128K max) — no RoPE scaling hack stacked on top, unlike the earlier Qwen2.5 attempt. Targets Hermes's 64K context floor with margin. |
| `KV_CACHE_DTYPE` | `fp8` | Needed to fit 65536 tokens of KV-cache in the VRAM left after weights at `GPU_MEM_UTIL=0.80`. |
| `GPU_MEM_UTIL` | `0.80` | The RTX 3080 is a desktop card (~9.64GiB usable, not a headless 10GB+ server part) — `0.90` OOM'd at CUDA-graph-capture startup on an earlier model; started conservative again for the same reason. |
| `TOOL_CALL_PARSER` | `llama3_json` | Must match the model family (`hermes` for Qwen2/2.5/Hermes, `mistral` for Mistral, `gemma4` for Gemma 4) — mismatched, this model spuriously calls tools on plain messages. |
| `CHAT_TEMPLATE` | `/vllm-workspace/examples/tool_chat_template_llama3.2_json.jinja` | Must match `TOOL_CALL_PARSER`. |
| `SERVED_MODEL_NAME` | `llama-3.2-3b-instruct-awq` | Slash-free alias for the API-facing `model` field — the raw `MODEL_ID` contains a `/`, which collides with agent configs that parse model refs as `provider/model`. |

HF weights cache on a `cheeky` hostPath (`/srv/openclaw/vllm-cache` — path
name predates the local-llm rename, kept as-is rather than churn a working
mount).

`enableServiceLinks: false` is set deliberately: k8s auto-injects
Docker-links env vars for every Service in the namespace (`VLLM_PORT`,
`VLLM_SERVICE_HOST`, ...), which collides with vLLM's own `VLLM_PORT` env
var and crashes `EngineCore` on startup.

### Deploy

```bash
kubectl apply -f kubernetes/00-namespace.yaml
sudo mkdir -p /srv/openclaw/vllm-cache   # on cheeky
kubectl -n local-llm create secret generic vllm-api-key \
  --from-literal=key="$(openssl rand -hex 32)"
kubectl apply -k kubernetes/
```

Needs `cheeky` GPU-wired first — NVIDIA driver + `nvidia-container-toolkit`
installed on the host, then `nvidia-gpu-plugin` applied (see the top-level
[README.md](../README.md)'s node-join docs and
[platform/nvidia-gpu-plugin/kustomization.yaml](../platform/nvidia-gpu-plugin/kustomization.yaml)).
`homelab apply llm` does the plugin + this in one step.

First boot downloads and quantizes weights — the readiness probe's
`failureThreshold: 80` accounts for that, not a misconfigured timeout.

## Open WebUI

`kubernetes/30-open-webui.yaml`, pinned to `cheeky-mini` (no GPU needed —
just proxies HTTP to vLLM over `vllm.local-llm.svc.cluster.local:8000/v1`).
Image `ghcr.io/open-webui/open-webui:main`, port `8080`, ClusterIP pinned
`10.43.200.52`. `WEBUI_AUTH=true`. Data on a `cheeky-mini` hostPath
(`/srv/openclaw/open-webui-data`). Memory limit is `3Gi` — the bundled
sentence-transformers embedding model (torch) alone exceeded a `1Gi` request
and got OOM-killed during initial sizing.

Chat testing / model debugging only — day-to-day agent traffic goes through
Hermes, not this.

### Expose (tailnet-only)

```bash
sudo tailscale serve --bg --https=8094 http://10.43.200.52:8080
```
Or `homelab serve` (re-establishes every tailnet binding in the repo).

## Notes

- Model swaps are exercised through env vars specifically so a bad choice
  (context-length OOM, tool-parser mismatch, degenerate output past a
  model's real context window) is a rollout restart to revert, not a
  manifest surgery. See `10-vllm.yaml`'s inline comments for the full
  rejected-options history before trying to extend context past a model's
  native window again — static YaRN scaling was tried once and produced
  clean boots with repetition-loop garbage on real prompts.
