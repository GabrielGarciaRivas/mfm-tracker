#!/usr/bin/env python3
"""Free Market Tracker shared price server.

A small self-hosted database that several copies of Free Market Tracker sync their
price sightings with, so a group of players shares one set of prices.

  python mfm_server.py serve                 run the server (what the Docker image does)
  python mfm_server.py add-key NAME          make an access key for a player
  python mfm_server.py list-keys             show who has a key
  python mfm_server.py remove-key NAME       take a key away
  python mfm_server.py stats                 how much is stored

Settings (environment variables):
  MFM_PORT        port to listen on (default 8765)
  MFM_DATA        folder for the database (default /data, or ./data outside Docker)
  MFM_NAME        a name for this server, shown in the app (default "Shared prices")
  MFM_KEEP_DAYS   sightings not seen for this many days are deleted (default 30, 0 = keep)
  MFM_TLS_CERT    with MFM_TLS_KEY: serve HTTPS with this certificate (PEM files)
  MFM_TLS_KEY

API (JSON over HTTP; every /api call needs "Authorization: Bearer <access key>"):
  GET  /api/v1/status                      {"name", "version", "sightings", "seq", "you"}
  POST /api/v1/sightings                   {"sightings": [ {uid, ts, item, price, qty, shop,
                                           seller, map, channel, sold, sold_ts, last_seen,
                                           notes}, ... ]}  (at most 500 at a time)
                                           -> {"seq", "same": {your uid: stored uid}}
  GET  /api/v1/sightings?since=SEQ&limit=N -> {"sightings": [... with "seq", "by"], "seq",
                                           "more": bool}
Every stored or changed sighting gets the next "seq" number, so a client asks for
everything after the last number it has seen.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import ssl
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

VERSION = "1.0.0"
UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"
MAX_BATCH = 500
MAX_BODY = 2_000_000
FIELDS = ("ts", "item", "price", "qty", "shop", "seller", "map", "channel", "sold", "sold_ts",
          "last_seen", "notes")


def data_dir() -> Path:
    d = os.environ.get("MFM_DATA") or ("/data" if Path("/.dockerenv").exists() else "data")
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


DB_PATH = data_dir() / "mfm-server.db"
_lock = threading.Lock()          # one writer at a time


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime(UTC_FMT)


def log(msg: str) -> None:
    print(f"{utc_now()} {msg}", flush=True)


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS sightings (
            uid TEXT PRIMARY KEY,
            seq INTEGER NOT NULL,
            ts TEXT NOT NULL,
            item TEXT NOT NULL,
            price INTEGER NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1,
            shop TEXT, seller TEXT, map TEXT, channel TEXT,
            sold INTEGER NOT NULL DEFAULT 0,
            sold_ts TEXT, last_seen TEXT, notes TEXT,
            added_by TEXT, updated_by TEXT, updated TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_seq ON sightings(seq);
        CREATE INDEX IF NOT EXISTS idx_item_price ON sightings(item, price);
        CREATE TABLE IF NOT EXISTS keys (
            name TEXT PRIMARY KEY,
            key_hash TEXT NOT NULL,
            created TEXT
        );
        CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
    """)
    return con


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def add_key(con, name: str) -> str:
    key = "mfm_" + secrets.token_urlsafe(24)
    con.execute("INSERT OR REPLACE INTO keys (name, key_hash, created) VALUES (?,?,?)",
                (name, _hash(key), utc_now()))
    con.commit()
    return key


def who(con, key: str) -> str | None:
    h = _hash(key)
    for name, kh in con.execute("SELECT name, key_hash FROM keys"):
        if hmac.compare_digest(kh, h):
            return name
    return None


def next_seq(con) -> int:
    row = con.execute("SELECT v FROM meta WHERE k = 'seq'").fetchone()
    n = int(row[0]) + 1 if row else 1
    con.execute("INSERT OR REPLACE INTO meta (k, v) VALUES ('seq', ?)", (str(n),))
    return n


def last_seq(con) -> int:
    row = con.execute("SELECT v FROM meta WHERE k = 'seq'").fetchone()
    return int(row[0]) if row else 0


# --------------------------------------------------------------------------- sightings

def _clean(s: dict) -> dict | None:
    """A sighting from a client, checked and tidied; None if it's not usable."""
    def text(v, n=200):
        v = "" if v is None else str(v).strip()
        return v[:n] or None

    def when(v):
        v = text(v, 30)
        return v if v and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", v) else None
    try:
        price = int(s.get("price"))
        qty = int(s.get("qty") or 1)
    except (TypeError, ValueError):
        return None
    uid, ts, item = text(s.get("uid"), 64), when(s.get("ts")), text(s.get("item"), 120)
    if not uid or not ts or not item or price <= 0 or qty <= 0:
        return None
    return {"uid": uid, "ts": ts, "item": item, "price": price, "qty": qty, "shop": text(s.get("shop")),
            "seller": text(s.get("seller"), 40), "map": text(s.get("map")), "channel": text(s.get("channel"), 8),
            "sold": 1 if s.get("sold") in (1, True, "1", "true") else 0, "sold_ts": when(s.get("sold_ts")),
            "last_seen": when(s.get("last_seen")) or ts, "notes": text(s.get("notes"), 300)}


def _same_shop(a: dict, b: dict) -> bool:
    if a["seller"] and b["seller"]:
        return a["seller"].lower() == b["seller"].lower()
    return bool(a["shop"]) and (a["shop"] or "").lower() == (b["shop"] or "").lower() \
        and (a["map"] or "") == (b["map"] or "")


def _find_same(con, s: dict) -> str | None:
    """A stored sighting of the same listing (same item, price and shop within a day),
    logged by someone else, so it isn't stored twice."""
    t = datetime.strptime(s["ts"], UTC_FMT)
    lo, hi = ((t + timedelta(hours=h)).strftime(UTC_FMT) for h in (-24, 24))
    cols = ("uid",) + FIELDS
    for row in con.execute(f"SELECT {', '.join(cols)} FROM sightings WHERE item = ? AND price = ? "
                           "AND ts BETWEEN ? AND ?", (s["item"], s["price"], lo, hi)):
        r = dict(zip(cols, row))
        if _same_shop(r, s):
            return r["uid"]
    return None


def store(con, sightings: list[dict], by: str) -> tuple[int, dict]:
    """Add or update sightings; returns (latest seq, {sent uid: stored uid} for ones that
    turned out to be a listing already stored under another uid)."""
    same = {}
    with _lock:
        for raw in sightings:
            s = _clean(raw) if isinstance(raw, dict) else None
            if not s:
                continue
            cur = con.execute("SELECT sold, sold_ts, last_seen, notes FROM sightings WHERE uid = ?",
                              (s["uid"],)).fetchone()
            uid = s["uid"]
            if not cur:
                other = _find_same(con, s)
                if other:
                    same[uid] = other
                    uid = other
                    cur = con.execute("SELECT sold, sold_ts, last_seen, notes FROM sightings WHERE uid = ?",
                                      (uid,)).fetchone()
            if cur:
                # a sighting seen again: it stays sold once sold, keeps its latest
                # last-seen time and its note unless a new one is given
                sold, sold_ts, last_seen, notes = cur
                new = {"sold": max(sold, s["sold"]),
                       "sold_ts": min(x for x in (sold_ts, s["sold_ts"]) if x) if (sold_ts or s["sold_ts"]) else None,
                       "last_seen": max(last_seen or "", s["last_seen"] or ""),
                       "notes": s["notes"] or notes,
                       "channel": s["channel"]}
                if (new["sold"], new["sold_ts"], new["last_seen"], new["notes"]) == (sold, sold_ts, last_seen, notes):
                    continue                    # nothing new
                con.execute("UPDATE sightings SET sold=?, sold_ts=?, last_seen=?, notes=?, "
                            "channel=COALESCE(?, channel), seq=?, updated_by=?, updated=? WHERE uid=?",
                            (new["sold"], new["sold_ts"], new["last_seen"], new["notes"], new["channel"],
                             next_seq(con), by, utc_now(), uid))
            else:
                con.execute("INSERT INTO sightings (uid, seq, ts, item, price, qty, shop, seller, map, channel, sold, "
                            "sold_ts, last_seen, notes, added_by, updated_by, updated) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (uid, next_seq(con), s["ts"], s["item"], s["price"], s["qty"], s["shop"], s["seller"],
                             s["map"], s["channel"], s["sold"], s["sold_ts"], s["last_seen"], s["notes"],
                             by, by, utc_now()))
        con.commit()
        return last_seq(con), same


def changes(con, since: int, limit: int) -> tuple[list[dict], int, bool]:
    cols = ("uid", "seq") + FIELDS + ("added_by",)
    rows = con.execute(f"SELECT {', '.join(cols)} FROM sightings WHERE seq > ? ORDER BY seq LIMIT ?",
                       (since, limit + 1)).fetchall()
    more = len(rows) > limit
    out = []
    for row in rows[:limit]:
        r = dict(zip(cols, row))
        r["by"] = r.pop("added_by")
        out.append(r)
    return out, (out[-1]["seq"] if out else since), more


def prune(con, days: int) -> int:
    if days <= 0:
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(UTC_FMT)
    with _lock:
        n = con.execute("DELETE FROM sightings WHERE COALESCE(last_seen, ts) < ?", (cutoff,)).rowcount
        con.commit()
    return n


# --------------------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = f"mfm-server/{VERSION}"
    con: sqlite3.Connection = None   # set in serve()

    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _who(self) -> str | None:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        return who(self.con, auth[7:].strip())

    def log_message(self, fmt, *args):
        pass                          # quiet; errors are logged below

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/health"):
            body = (f"Free Market Tracker server {VERSION} is running.\n"
                    "Connect to it from the app: Shared Database.\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        name = self._who()
        if name is None:
            return self._send(401, {"error": "Missing or wrong access key."})
        if url.path == "/api/v1/status":
            n = self.con.execute("SELECT COUNT(*) FROM sightings").fetchone()[0]
            return self._send(200, {"name": os.environ.get("MFM_NAME", "Shared prices"), "version": VERSION,
                                    "sightings": n, "seq": last_seq(self.con), "you": name})
        if url.path == "/api/v1/sightings":
            q = parse_qs(url.query)
            try:
                since = int(q.get("since", ["0"])[0])
                limit = max(1, min(5000, int(q.get("limit", ["2000"])[0])))
            except ValueError:
                return self._send(400, {"error": "since and limit must be numbers"})
            rows, seq, more = changes(self.con, since, limit)
            return self._send(200, {"sightings": rows, "seq": seq, "more": more})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        name = self._who()
        if name is None:
            return self._send(401, {"error": "Missing or wrong access key."})
        if urlparse(self.path).path != "/api/v1/sightings":
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._send(413, {"error": "too much at once"})
        try:
            body = json.loads(self.rfile.read(n))
            sightings = body["sightings"]
            assert isinstance(sightings, list) and len(sightings) <= MAX_BATCH
        except Exception:
            return self._send(400, {"error": f'send {{"sightings": [...]}} with at most {MAX_BATCH}'})
        try:
            seq, same = store(self.con, sightings, name)
        except Exception as e:
            log(f"store failed: {type(e).__name__}: {e}")
            return self._send(500, {"error": "server error"})
        self._send(200, {"seq": seq, "same": same})


def serve() -> None:
    port = int(os.environ.get("MFM_PORT", "8765"))
    con = db()
    if not con.execute("SELECT 1 FROM keys LIMIT 1").fetchone():
        key = add_key(con, "admin")
        log("No access keys yet: made one named 'admin'. Give it to a player, or make one per "
            "player with: add-key NAME")
        log(f"Access key for 'admin': {key}")
    Handler.con = con
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    cert, key = os.environ.get("MFM_TLS_CERT"), os.environ.get("MFM_TLS_KEY")
    scheme = "http"
    if cert and key:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"
    keep = int(os.environ.get("MFM_KEEP_DAYS", "30"))

    def housekeeping():
        while True:
            try:
                n = prune(con, keep)
                if n:
                    log(f"deleted {n} sightings not seen for {keep} days")
            except Exception as e:
                log(f"clean-up failed: {e}")
            time.sleep(6 * 3600)
    threading.Thread(target=housekeeping, daemon=True).start()
    log(f"Free Market Tracker server {VERSION} on {scheme}://0.0.0.0:{port} (data: {DB_PATH})")
    httpd.serve_forever()


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "serve"
    if cmd == "serve":
        serve()
        return 0
    con = db()
    if cmd == "add-key" and len(argv) == 3:
        print(f"Access key for '{argv[2]}': {add_key(con, argv[2])}")
        print("Give it to that player; they paste it into Shared Database in the app.")
        return 0
    if cmd == "list-keys":
        for name, created in con.execute("SELECT name, created FROM keys ORDER BY name"):
            print(f"{name}\t(made {created})")
        return 0
    if cmd == "remove-key" and len(argv) == 3:
        n = con.execute("DELETE FROM keys WHERE name = ?", (argv[2],)).rowcount
        con.commit()
        print("Removed." if n else "No key with that name.")
        return 0
    if cmd == "stats":
        n = con.execute("SELECT COUNT(*) FROM sightings").fetchone()[0]
        items = con.execute("SELECT COUNT(DISTINCT item) FROM sightings").fetchone()[0]
        print(f"{n} sightings of {items} items; {DB_PATH.stat().st_size / 1e6:.1f} MB")
        for name, c in con.execute("SELECT added_by, COUNT(*) FROM sightings GROUP BY added_by ORDER BY 2 DESC"):
            print(f"  {name}: {c}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
