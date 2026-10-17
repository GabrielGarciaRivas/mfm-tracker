"""Shared Database: price sightings kept in sync with a self-hosted Free Market Tracker
server (see server/README.md), so a group of players shares one set of prices.

- You connect with the server's address and your access key (from whoever runs it).
- New sightings of items in the item list are sent to the server; sightings that
  change (sold, seen again, a note) are sent again; everyone's sightings are copied
  into the local prices every few seconds.
- Names that end up in Review are only sent once they're matched to an item.
- Megaphones are shared too. When several players read the same megaphone, the read
  the OCR was most sure of is kept (on the server and here). The server keeps them for
  72 hours; you get the ones from the time set in your Megaphones tab.

Local bookkeeping lives in prices.db: listings.uid (the sighting's id on the
server), listings.shared (NULL = local only, 0 = to send, 1 = on the server),
listings.shared_sig (its values when last synced: a change means "send again"),
and the table shared_state (how far the server's changes have been read).
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta

import mfm

FIELDS = ("item", "price", "qty", "shop", "seller", "map", "channel", "sold", "sold_ts", "last_seen", "notes")
DEFAULT_PORT = 8765


class SharedError(Exception):
    """Something the user can act on (wrong key, server not reachable ...)."""


def normalize_url(addr: str) -> str:
    """'myhost', 'myhost:8765' or 'http://myhost:8765/' -> 'http://myhost:8765'."""
    addr = (addr or "").strip().rstrip("/")
    if not addr:
        return ""
    if "://" not in addr:
        addr = "http://" + addr
    u = urllib.parse.urlparse(addr)
    if not u.hostname:
        return ""
    port = u.port or (DEFAULT_PORT if u.scheme == "http" else None)
    host = f"[{u.hostname}]" if ":" in u.hostname else u.hostname
    return f"{u.scheme}://{host}" + (f":{port}" if port else "")


class Server:
    """The server's API, with your access key."""

    def __init__(self, url: str, key: str):
        self.url, self.key = normalize_url(url), (key or "").strip()
        if not self.url:
            raise SharedError("Enter the server's address, e.g. 203.0.113.5:8765 or prices.example.com:8765.")
        if not self.key:
            raise SharedError("Enter your access key.")

    def call(self, method: str, path: str, body=None, query: dict | None = None) -> dict:
        url = self.url + path + ("?" + urllib.parse.urlencode(query) if query else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.key}", "User-Agent": mfm.USER_AGENT,
            "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20, context=mfm.ssl_context()) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise SharedError("The server didn't accept your access key.") from None
            try:
                msg = json.loads(e.read() or b"{}").get("error", "")
            except ValueError:
                msg = ""
            raise SharedError(f"Server error {e.code}" + (f": {msg}" if msg else "")) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            reason = getattr(e, "reason", e)
            raise SharedError(f"Can't reach the server ({reason}). Check the address, and that it's running "
                              "and its port is forwarded.") from None
        except ValueError:
            raise SharedError("That address doesn't answer like a Free Market Tracker server.") from None

    def status(self) -> dict:
        st = self.call("GET", "/api/v1/status")
        if "seq" not in st:
            raise SharedError("That address doesn't answer like a Free Market Tracker server.")
        return st

    def send(self, sightings: list[dict]) -> dict:
        return self.call("POST", "/api/v1/sightings", {"sightings": sightings})

    def changes(self, since: int) -> dict:
        return self.call("GET", "/api/v1/sightings", query={"since": since, "limit": 2000})

    def send_megaphones(self, megaphones: list[dict]) -> dict:
        return self.call("POST", "/api/v1/megaphones", {"megaphones": megaphones})

    def megaphone_changes(self, since: int, hours: float) -> dict:
        return self.call("GET", "/api/v1/megaphones", query={"since": since, "hours": hours, "limit": 2000})


# --------------------------------------------------------------------------- local side

def prepare(con) -> None:
    con.execute("CREATE INDEX IF NOT EXISTS idx_listings_uid ON listings(uid)")
    con.execute("CREATE TABLE IF NOT EXISTS shared_state (server TEXT PRIMARY KEY, seq INTEGER)")
    con.commit()


MEGA_SERVER_HOURS = 72     # how long the server keeps megaphones


def _mega_sig(r: dict) -> str:
    return json.dumps([str(r.get(k) or "") for k in ("player", "channel", "message")] + [float(r.get("conf") or 0)])


def reset_megaphones(con, url: str) -> None:
    """Read the server's megaphones from the start again (e.g. after you chose to see
    more hours of them)."""
    prepare(con)
    con.execute("DELETE FROM shared_state WHERE server = ?", (normalize_url(url) + "#megaphones",))
    con.commit()


def _sig(r: dict) -> str:
    return json.dumps([("" if r.get(f) is None else str(r[f])) for f in FIELDS])


def _same_listing(con, r: dict, hours: int = 24) -> int | None:
    """A local sighting not on the server yet that is this one (same item, price, player
    or shop, and map, within a day): two people logged the same listing."""
    try:
        t = datetime.strptime(r["ts"], mfm.UTC_FMT)
    except (ValueError, TypeError):
        return None
    lo, hi = ((t + timedelta(hours=d)).strftime(mfm.UTC_FMT) for d in (-hours, hours))
    for rid, title, seller, mp in con.execute(
            "SELECT id, shop, seller, map FROM listings WHERE item = ? AND price = ? AND uid IS NULL "
            "AND ts BETWEEN ? AND ?", (r["item"], r["price"], lo, hi)):
        if mfm._same_shop(title, seller, mp, r.get("shop") or "", r.get("seller") or "", r.get("map") or ""):
            return rid
    return None


class SharedSync:
    """Keeps prices.db and the server in step, in a background thread: every few
    seconds new and changed sightings are sent, and everyone's changes read.
    `on_status(dict)` hears how it's going: {"ok": bool, "text": str, ...}."""

    EVERY = 4.0

    def __init__(self, cfg: dict, url: str, key: str, on_status=lambda s: None, on_new_rows=lambda n: None,
                 on_megaphones=lambda n: None):
        self.cfg = cfg
        self.on_megaphones = on_megaphones
        self.server = Server(url, key)
        self.on_status, self.on_new_rows = on_status, on_new_rows
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.thread: threading.Thread | None = None
        self.sent = self.received = 0
        self.ok = False
        self.info: dict = {}

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.wake.set()
        mfm.SHARE_NEW = False

    def _status(self, ok: bool, text: str) -> None:
        self.ok = ok
        self.on_status({"ok": ok, "text": text, "sent": self.sent, "received": self.received,
                        "server": self.info.get("name", ""), "you": self.info.get("you", "")})

    def _run(self) -> None:
        con = mfm.db()
        prepare(con)
        mfm.SHARE_NEW = True                  # new sightings are marked to be sent
        while not self.stop_event.is_set():
            try:
                if not self.info:
                    self.info = self.server.status()
                self._send(con)
                self._receive(con)
                self._send_megaphones(con)
                self._receive_megaphones(con)
                self._status(True, "Connected")
            except SharedError as e:
                self.info = {}
                self._status(False, str(e))
                self.stop_event.wait(15)
                continue
            except Exception as e:
                self._status(False, f"{type(e).__name__}: {e}")
            self.wake.wait(self.EVERY)
            self.wake.clear()
        con.close()

    # -- local -> server
    def _send(self, con) -> None:
        if not mfm.has_item_list():
            return                            # can't tell real items from misreads
        # new ones (names still in Review wait until they're matched to an item)
        ids = [rid for rid, item in con.execute("SELECT id, item FROM listings WHERE shared = 0 ORDER BY id")
               if mfm.is_known_item(item)][:500]
        cols = ("id", "uid", "shared_sig", "ts") + FIELDS
        rows = []
        if ids:
            rows += [dict(zip(cols, r)) for r in con.execute(
                f"SELECT {', '.join(cols)} FROM listings WHERE id IN ({','.join('?' * len(ids))})", ids)]
        # changed since they were last synced (sold, seen again, a note)
        for r in con.execute(f"SELECT {', '.join(cols)} FROM listings WHERE shared = 1 AND uid IS NOT NULL "
                             "AND COALESCE(last_seen, ts) >= ?", (mfm.utc_ago(days=7),)):
            r = dict(zip(cols, r))
            if _sig(r) != r["shared_sig"] and len(rows) < 500:
                rows.append(r)
        if not rows:
            return
        for r in rows:
            if not r["uid"]:
                r["uid"] = uuid.uuid4().hex
        payload = [{k: r[k] for k in ("uid", "ts") + FIELDS} for r in rows]
        res = self.server.send(payload)
        same = res.get("same", {})
        for r in rows:
            con.execute("UPDATE listings SET uid = ?, shared = 1, shared_sig = ? WHERE id = ?",
                        (same.get(r["uid"], r["uid"]), _sig(r), r["id"]))
        con.commit()
        self.sent += sum(1 for r in rows if r["id"] in ids)

    # -- server -> local
    def _receive(self, con) -> None:
        url = self.server.url
        row = con.execute("SELECT seq FROM shared_state WHERE server = ?", (url,)).fetchone()
        seq = row[0] if row else 0
        keep_days = self.cfg.get("keep_days", 30) if self.cfg.get("retention", "archive") != "keep" else None
        oldest = mfm.utc_ago(days=keep_days) if keep_days else ""
        has_list = mfm.has_item_list()
        new = 0
        while True:
            res = self.server.changes(seq)
            for r in res.get("sightings", []):
                if oldest and (r.get("last_seen") or r["ts"]) < oldest:
                    continue                  # older than you keep prices for
                if has_list and not mfm.is_known_item(r["item"]):
                    continue
                sig = _sig(r)
                local = con.execute("SELECT id, shared_sig FROM listings WHERE uid = ?", (r["uid"],)).fetchall()
                if local:
                    for rid, old in local:
                        if old != sig:        # changed on the server: take it
                            con.execute("UPDATE listings SET item=?, price=?, qty=?, shop=?, seller=?, map=?, "
                                        "channel=?, sold=?, sold_ts=?, last_seen=?, notes=?, shared=1, shared_sig=? "
                                        "WHERE id=?", tuple(r.get(f) for f in FIELDS) + (sig, rid))
                    continue
                same = _same_listing(con, r)
                if same:                      # yours, not sent yet: it's this one
                    con.execute("UPDATE listings SET uid=?, shared=1, shared_sig=?, sold=MAX(COALESCE(sold,0),?), "
                                "last_seen=MAX(COALESCE(last_seen,ts),?) WHERE id=?",
                                (r["uid"], sig, r.get("sold") or 0, r.get("last_seen") or r["ts"], same))
                    continue
                con.execute(
                    "INSERT INTO listings (ts, item, price, qty, shop, seller, map, channel, raw, session, sold, "
                    "last_seen, sold_ts, notes, uid, shared, shared_sig) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)",
                    (r["ts"], r["item"], r["price"], r.get("qty") or 1, r.get("shop"), r.get("seller"), r.get("map"),
                     r.get("channel"), f"shared by {r.get('by') or 'someone'}", "shared", r.get("sold") or 0,
                     r.get("last_seen") or r["ts"], r.get("sold_ts"), r.get("notes"), r["uid"], sig))
                new += 1
            seq = res.get("seq", seq)
            con.execute("INSERT OR REPLACE INTO shared_state (server, seq) VALUES (?, ?)", (url, seq))
            con.commit()
            if not res.get("more"):
                break
        if new:
            self.received += new
            self.on_new_rows(new)


    # -- megaphones
    def _send_megaphones(self, con) -> None:
        cols = ("id", "uid", "shared_sig", "ts", "player", "channel", "message", "kind", "color", "conf")
        rows = []
        for r in con.execute(f"SELECT {', '.join(cols)} FROM megaphones WHERE kind IS NOT NULL AND ts >= ? "
                             "ORDER BY id", (mfm.utc_ago(hours=MEGA_SERVER_HOURS),)):
            r = dict(zip(cols, r))
            if not r["uid"] or _mega_sig(r) != r["shared_sig"]:
                rows.append(r)
        if not rows:
            return
        rows = rows[:500]
        for r in rows:
            if not r["uid"]:
                r["uid"] = uuid.uuid4().hex
        res = self.server.send_megaphones([{k: r[k] for k in cols[3:] + ("uid",)} for r in rows])
        same = res.get("same", {})
        for r in rows:
            con.execute("UPDATE megaphones SET uid = ?, shared_sig = ? WHERE id = ?",
                        (same.get(r["uid"], r["uid"]), _mega_sig(r), r["id"]))
        con.commit()

    def _receive_megaphones(self, con) -> None:
        key = self.server.url + "#megaphones"
        row = con.execute("SELECT seq FROM shared_state WHERE server = ?", (key,)).fetchone()
        seq = row[0] if row else 0
        hours = max(1, min(MEGA_SERVER_HOURS, float(self.cfg.get("megaphone_hours", 24) or 24)))
        new = 0
        while True:
            res = self.server.megaphone_changes(seq, hours)
            for m in res.get("megaphones", []):
                conf = float(m.get("conf") or 0)
                sig = _mega_sig(m)
                local = con.execute("SELECT id, conf FROM megaphones WHERE uid = ?", (m["uid"],)).fetchone()
                if not local:
                    same = mfm.find_megaphone(con, m["ts"], m["player"], m.get("channel"), m["message"])
                    if same:
                        local = (same[0], same[4])
                        con.execute("UPDATE megaphones SET uid = ? WHERE id = ?", (m["uid"], same[0]))
                if local:
                    if conf >= float(local[1] or 0):   # the server's read is at least as sure: take it
                        con.execute("UPDATE megaphones SET player=?, channel=COALESCE(?, channel), message=?, kind=?, "
                                    "conf=?, shared_sig=? WHERE id=?",
                                    (m["player"], m.get("channel"), m["message"], mfm.megaphone_kind(m["message"]),
                                     conf, sig, local[0]))
                    continue
                con.execute("INSERT INTO megaphones (ts, seen, player, channel, message, kind, color, conf, uid, "
                            "shared_sig) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (m["ts"], mfm.utc_now(), m["player"], m.get("channel"), m["message"],
                             mfm.megaphone_kind(m["message"]), m.get("color"), conf, m["uid"], sig))
                new += 1
            seq = res.get("seq", seq)
            con.execute("INSERT OR REPLACE INTO shared_state (server, seq) VALUES (?, ?)", (key, seq))
            con.commit()
            if not res.get("more"):
                break
        if new:
            self.on_megaphones(new)


def check(url: str, key: str) -> dict:
    """Connect once: the server's status (its name, and your name on it)."""
    return Server(url, key).status()
