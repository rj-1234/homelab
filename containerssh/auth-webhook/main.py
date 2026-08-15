"""ContainerSSH auth webhook — fixed authorized public keys + one fixed
password, no user database.

Implements the ContainerSSH webhook contract: POST /pubkey with
{username, publicKey, ...}, POST /password with {username, passwordBase64,
...}, respond {success, authenticatedUsername}.
https://containerssh.io/v0.6/reference/auth-webhook/
"""
import base64
import hmac
import os

from flask import Flask, jsonify, request

app = Flask(__name__)


def _key_fields(key: str) -> str:
    # Compare only "<type> <base64>" — drop any trailing comment.
    parts = key.strip().split()
    return " ".join(parts[:2])


AUTHORIZED_KEYS = {
    _key_fields(line)
    for line in os.environ["AUTHORIZED_PUBLIC_KEYS"].splitlines()
    if line.strip()
}

# Wetty's --ssh-auth=password mode prompts interactively in the browser
# terminal each session — this is what actually delivers a per-session
# secret (the key-file mode doesn't, see containerssh/kubernetes/README.md).
AUTHORIZED_PASSWORD = os.environ.get("AUTHORIZED_PASSWORD", "")


@app.post("/pubkey")
def pubkey():
    body = request.get_json(force=True)
    username = body.get("username", "")
    submitted = body.get("publicKey", "")
    success = bool(submitted) and _key_fields(submitted) in AUTHORIZED_KEYS
    return jsonify({"success": success, "authenticatedUsername": username})


@app.post("/password")
def password():
    body = request.get_json(force=True)
    username = body.get("username", "")
    try:
        submitted = base64.b64decode(body.get("passwordBase64", "")).decode()
    except (ValueError, UnicodeDecodeError):
        submitted = ""
    success = bool(AUTHORIZED_PASSWORD) and hmac.compare_digest(submitted, AUTHORIZED_PASSWORD)
    return jsonify({"success": success, "authenticatedUsername": username})


@app.get("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
