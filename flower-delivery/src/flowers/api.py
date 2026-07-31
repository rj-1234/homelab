"""Digital Flower Delivery — backend.

Run: uvicorn flowers.api:app --host 0.0.0.0 --port 8000
"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb

from . import db

app = FastAPI(title="Digital Flower Delivery")

SPECIES = {"rose", "ranunculus", "tulip", "cosmos", "daffodil", "chamomile", "eucalyptus"}
LIFETIME_OPTIONS_MS = {
    24 * 3600_000,        # 24 hours
    3 * 24 * 3600_000,    # 3 days
    7 * 24 * 3600_000,    # 7 days
    30 * 24 * 3600_000,   # 30 days
}
MAX_STEMS = 13  # sender picks a bouquet size between 5-13 in the compose UI; server just enforces the outer bound
MAX_MESSAGE_LEN = 240


def _rows(sql, args=()):
    with db.connect() as c:
        cur = c.execute(sql, args)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _one(sql, args=()):
    r = _rows(sql, args)
    return r[0] if r else None


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/api/gifts")
async def create_gift(request: Request):
    body = await request.json()
    stems = body.get("stems") or []
    message = (body.get("message") or "").strip()
    sender = (body.get("sender") or "").strip()
    lifetime_ms = body.get("lifetime_ms")

    if not (1 <= len(stems) <= MAX_STEMS):
        return JSONResponse({"error": f"stems must have 1-{MAX_STEMS} entries"}, status_code=400)
    for stem in stems:
        if stem.get("species") not in SPECIES:
            return JSONResponse({"error": "invalid species"}, status_code=400)
    if not message or len(message) > MAX_MESSAGE_LEN:
        return JSONResponse({"error": f"message must be 1-{MAX_MESSAGE_LEN} chars"}, status_code=400)
    if not sender:
        return JSONResponse({"error": "sender is required"}, status_code=400)
    if lifetime_ms not in LIFETIME_OPTIONS_MS:
        return JSONResponse({"error": "invalid lifetime_ms"}, status_code=400)

    gift_id = secrets.token_urlsafe(16)
    with db.connect() as c:
        c.execute(
            "INSERT INTO gifts (id, stems, message, sender, lifetime_ms)"
            " VALUES (%s, %s, %s, %s, %s)",
            (gift_id, Jsonb(stems), message, sender, lifetime_ms),
        )

    return {"id": gift_id, "url": f"/g/{gift_id}"}


@app.get("/api/gifts/{gift_id}")
def get_gift(gift_id: str):
    row = _one(
        "SELECT stems, message, sender, lifetime_ms, opened_at, expires_at"
        " FROM gifts WHERE id = %s",
        (gift_id,),
    )
    if row is None:
        return JSONResponse({"error": "not_found"}, status_code=404)

    if row["opened_at"] is None:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(milliseconds=row["lifetime_ms"])
        with db.connect() as c:
            c.execute(
                "UPDATE gifts SET opened_at = %s, expires_at = %s WHERE id = %s",
                (now, expires_at, gift_id),
            )
        row["opened_at"] = now
        row["expires_at"] = expires_at

    alive = datetime.now(timezone.utc) < row["expires_at"]

    return {
        "stems": row["stems"],
        "message": row["message"],
        "sender": row["sender"],
        "expires_at": row["expires_at"].isoformat(),
        "alive": alive,
    }


@app.get("/api/admin/gifts")
def admin_list_gifts():
    rows = _rows(
        "SELECT id, stems, message, sender, lifetime_ms, created_at, opened_at, expires_at"
        " FROM gifts ORDER BY created_at DESC"
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        if row["opened_at"] is None:
            row["status"] = "not_opened"
        elif now < row["expires_at"]:
            row["status"] = "live"
        else:
            row["status"] = "expired"
        row["created_at"] = row["created_at"].isoformat()
        row["opened_at"] = row["opened_at"].isoformat() if row["opened_at"] else None
        row["expires_at"] = row["expires_at"].isoformat() if row["expires_at"] else None
    return rows


@app.delete("/api/admin/gifts/{gift_id}")
def admin_delete_gift(gift_id: str):
    row = _one("SELECT id FROM gifts WHERE id = %s", (gift_id,))
    if row is None:
        return JSONResponse({"error": "not_found"}, status_code=404)

    with db.connect() as c:
        c.execute("DELETE FROM gifts WHERE id = %s", (gift_id,))

    return {"ok": True}
