# ContainerSSH — on-demand, isolated SSH shells (native + web)

Every SSH connection spins up a fresh, throwaway Pod in `containerssh-guests`
and drops you into it; the pod is deleted the moment you disconnect. Not a
shell into an existing service — a brand new isolated container per session.
Tailnet-only, like every other admin service here. Two ways in, same
backend: native `ssh` (pubkey), or a browser terminal via Wetty (password).

```
you ──ssh:2222───────────────▶ ContainerSSH (containerssh ns) ──auth──▶ auth-webhook
you ──https:8098──▶ Wetty ──ssh:2222──▶        │                       (checks pubkey
                                                │                        OR password
                                                ▼                        against fixed
                                        spawns a Pod in                 Secret values)
                                        containerssh-guests
                                        (kubernetes backend, RBAC
                                        scoped to that namespace
                                        only) — deleted on disconnect
```

- **Auth**: no built-in user database in ContainerSSH — it requires an
  external webhook, OAuth2/OIDC, or Kerberos. Went with a minimal
  self-hosted webhook ([auth-webhook/](../auth-webhook/), ~50 lines) rather
  than an external OAuth dependency. It checks two independent things:
  a list of authorized public keys (native `ssh`), and one fixed password
  (Wetty). Built and pushed to the self-hosted Zot registry, same as
  Hermes Agent.
- **Why Wetty uses a password, not a key**: tried `--ssh-key` first (a
  dedicated passphrase-protected keypair, expecting `ssh`-style interactive
  passphrase prompting). Wetty's own startup log corrected that
  assumption: *"Password-less auth enabled using private key... anything
  that reaches the wetty server will be able to run remote operations
  without authentication."* Its key mode does its own client-side
  handshake and connects immediately — passphrase on the key file or not.
  `--ssh-auth=password` is the mode that actually prompts live in the
  browser terminal each session, so that's what's deployed. Real
  consequence: the password is a shared secret (not per-user), same trust
  shape as a login page — but it *is* something you must type every time,
  which was the actual goal (vs. reach-the-URL-get-a-shell).
- **Isolation**: `backend: kubernetes` — ContainerSSH's own ServiceAccount
  only has `create/delete/get/list/watch` on `pods` (+ `pods/log` get,
  `pods/exec` create) inside `containerssh-guests`, nothing else,
  nowhere else. Guest pods run with `automountServiceAccountToken: false`
  — no session gets a Kubernetes API token.
- **CPU-only, no GPU** — session pods aren't node-pinned or GPU-scheduled.
  `containerssh`, `containerssh-auth-webhook`, and `wetty` themselves *are*
  pinned to `cheeky-mini` — `cheeky`'s containerd doesn't currently pull
  from the Zot registry mirror correctly (`registries.yaml` present but
  not live — needs a `k3s-agent` restart on that node to pick it up,
  untouched so far since it needs sudo on the host).

## Prerequisites (host, out-of-band — not committed)
```bash
# Host key (ContainerSSH needs a stable key like any sshd)
ssh-keygen -t ed25519 -f hostkey -N "" -C containerssh-hostkey
kubectl -n containerssh create secret generic containerssh-hostkey \
  --from-file=ssh_host_ed25519_key=hostkey

# Authorized public key(s) for native `ssh` (newline-separated, one per line)
# + the fixed password Wetty's browser prompt checks against
kubectl -n containerssh create secret generic containerssh-authorized-key \
  --from-literal=AUTHORIZED_PUBLIC_KEYS="$(cat your_key.pub)" \
  --from-literal=AUTHORIZED_PASSWORD='<pick a real password>'
```
To rotate either later: delete + recreate the `containerssh-authorized-key`
Secret, then
`kubectl -n containerssh rollout restart deploy/containerssh-auth-webhook`.

## Deploy
```bash
kubectl apply -f containerssh/kubernetes/
```
(Namespaces + RBAC are idempotent; the auth-webhook image is built from
[../auth-webhook/](../auth-webhook/) — `docker build` + push to
`10.43.200.51:5000/containerssh-auth-webhook:latest`, rerun after any source
change.)

## Expose (tailnet-only)
Two different `tailscale serve` modes — ContainerSSH is raw SSH (`--tcp`),
Wetty is a normal web app (`--https`):
```bash
sudo tailscale serve --bg --tcp=2222 tcp://10.43.200.55:2222     # ContainerSSH
sudo tailscale serve --bg --https=8098 http://10.43.200.56:3000  # Wetty
```
Native `ssh` (pubkey, no prompt beyond the key itself):
```bash
ssh -p 2222 -i ~/.ssh/<your-key> anyuser@cheeky-mini.tail2f4253.ts.net
```
Browser (password, prompted live each session):
```
https://cheeky-mini.tail2f4253.ts.net:8098
```
(Port 2222, not 22 — the node's real sshd already owns 22.)

## Notes
- Config lives in the `containerssh-config` ConfigMap
  ([40-containerssh.yaml](40-containerssh.yaml)) — `-config` flag (not
  `-c`, the binary doesn't accept the short form). Webhook `url` fields are
  base URLs only; ContainerSSH appends `/pubkey`/`/password` itself.
- `/password`'s request field is `passwordBase64` (base64-encoded), not a
  plain `password` field — easy to get wrong, cost a debugging pass.
- Guest image defaults to `containerssh/containerssh-guest-image` (upstream
  default, minimal shell). Swap `kubernetes.pod.spec.containers[0].image`
  for anything else you want session pods to start from.
- No max-session-duration cap configured yet — sessions end when the SSH
  connection (native or Wetty's) closes, but a client that hangs without
  closing could leave a guest pod running. `kubectl -n containerssh-guests
  get pods` to check for stragglers; add a timeout if this becomes a real
  problem.
