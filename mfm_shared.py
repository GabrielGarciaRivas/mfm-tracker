"""Shared Database: price sightings kept in sync with a self-hosted Free Market Tracker
server (see server/README.md), so a group of players shares one set of prices.

- You sign in with the server's address, your user name and password (from whoever
  runs it). The app keeps the sign-in (a token from the server, not your password),
  so you don't have to sign in again.
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
    """Something the user can act on (server not reachable, wrong password ...)."""


class SignedOut(SharedError):
    """The server doesn't accept the saved sign-in any more: sign in again."""


LOGIN_PATH = mfm.SETTINGS_DIR / "shared_login.json"


def load_login() -> dict:
    """The saved sign-in: {"server", "username", "user_id", "token"}."""
    try:
        return json.loads(LOGIN_PATH.read_text())
    except (OSError, ValueError):
        return {}


def save_login(d: dict) -> None:
    mfm.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    LOGIN_PATH.write_text(json.dumps(d, indent=2))
    try:
        import os
        os.chmod(LOGIN_PATH, 0o600)
    except OSError:
        pass


def forget_login() -> None:
    LOGIN_PATH.unlink(missing_ok=True)


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
    """The server's API, signed in with a token."""

    def __init__(self, url: str, token: str | None = None):
        self.url, self.token = normalize_url(url), (token or "").strip()
        if not self.url:
            raise SharedError("Enter the server's address, e.g. 203.0.113.5:8765 or prices.example.com:8765.")

    def call(self, method: str, path: str, body=None, query: dict | None = None) -> dict:
        url = self.url + path + ("?" + urllib.parse.urlencode(query) if query else "")
        data = json.dumps(body).encode() if body is not None else None
        headers = {"User-Agent": mfm.USER_AGENT, "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20, context=mfm.ssl_context()) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read() or b"{}").get("error", "")
            except ValueError:
                msg = ""
            if e.code == 401:
                if path == "/api/v1/login":
                    raise SharedError(msg or "Wrong user name or password.") from None
                raise SignedOut("Your sign-in has ended: enter your password and connect again.") from None
            if e.code in (403, 429) and msg:
                raise SharedError(msg) from None
            raise SharedError(f"Server error {e.code}" + (f": {msg}" if msg else "")) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            reason = getattr(e, "reason", e)
            raise SharedError(f"Can't reach the server ({reason}). Check the address, and that it's running "
                              "and its port is forwarded.") from None
        except ValueError:
            raise SharedError("That address doesn't answer like a Free Market Tracker server.") from None

    def login(self, username: str, password: str) -> dict:
        r = self.call("POST", "/api/v1/login", {"username": username.strip(), "password": password})
        if not r.get("token"):
            raise SharedError("That address doesn't answer like a Free Market Tracker server.")
        self.token = r["token"]
        return r

    def logout(self) -> None:
        self.call("POST", "/api/v1/logout", {})

    def change_password(self, old: str, new: str) -> None:
        self.call("POST", "/api/v1/password", {"password": old, "new_password": new})

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

    def send_nicknames(self, nicknames: list[dict]) -> dict:
        return self.call("POST", "/api/v1/nicknames", {"nicknames": nicknames})

    def nickname_changes(self, since: int) -> dict:
        return self.call("GET", "/api/v1/nicknames", query={"since": since, "limit": 5000})


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


def _nick_sig(item, deleted) -> str:
    return json.dumps([item or "", 1 if deleted else 0])


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

    def __init__(self, cfg: dict, url: str, token: str, on_status=lambda s: None, on_new_rows=lambda n: None,
                 on_megaphones=lambda n: None):
        self.cfg = cfg
        self.on_megaphones = on_megaphones
        self.server = Server(url, token)
        self.on_status, self.on_new_rows = on_status, on_new_rows
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.thread: threading.Thread | None = None
        self.sent = self.received = 0
        self.mega_sent = self.mega_received = 0
        self.ok = False
        self.info: dict = {}
        self.caught_up = False

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.wake.set()
        mfm.SHARE_NEW = False

    def _status(self, ok: bool, text: str, **more) -> None:
        self.ok = ok
        you = self.info.get("you", "")
        self.on_status({"ok": ok, "text": text, "sent": self.sent, "received": self.received,
                        "mega_sent": self.mega_sent, "mega_received": self.mega_received,
                        "server": self.info.get("name", ""), "version": self.info.get("version", ""),
                        "you": you.get("name", "") if isinstance(you, dict) else you, **more})

    def _run(self) -> None:
        con = mfm.db()
        prepare(con)
        mfm.SHARE_NEW = True                  # new sightings are marked to be sent
        while not self.stop_event.is_set():
            try:
                if not self.info:
                    self.info = self.server.status()
                    self.caught_up = False
                if not self.caught_up:
                    # every time it (re)connects: send what was logged while offline and
                    # read everything on the server again, for sightings and megaphones
                    self._status(True, "Catching up with the server…")
                    self._true_up(con)
                    self.caught_up = True
                self._send(con)
                self._receive(con)
                self._send_megaphones(con)
                self._receive_megaphones(con)
                self._send_nicknames(con)
                self._receive_nicknames(con)
                self._status(True, "Connected")
            except SignedOut as e:
                forget_login()                # the token is no good any more
                self._status(False, str(e), signed_out=True)
                mfm.SHARE_NEW = False
                break
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
    def _send(self, con, changed_days: float = 7) -> int:
        """Send new and changed sightings (at most 500); returns how many were sent."""
        if not mfm.has_item_list():
            return 0                          # can't tell real items from misreads
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
                             "AND COALESCE(last_seen, ts) >= ?", (mfm.utc_ago(days=changed_days),)):
            r = dict(zip(cols, r))
            if _sig(r) != r["shared_sig"] and len(rows) < 500:
                rows.append(r)
        if not rows:
            return 0
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
        return len(rows)

    def _keep_days(self) -> float:
        """How far back sightings are kept: the server's limit or yours, whichever is less."""
        mine = self.cfg.get("keep_days", 30) if self.cfg.get("retention", "archive") != "keep" else 3650
        server = self.info.get("keep_days") or 30
        return max(1, min(float(mine), float(server) if server > 0 else 3650))

    def _true_up(self, con) -> None:
        """Catch up after being offline (or on first connecting):
        - sightings logged here while not connected are sent (as far back as sightings
          are kept), and so are changes made to shared ones (sold, seen again, notes);
        - megaphones read here while not connected are sent, and so are nicknames
          taught here;
        - everything on the server is read again, so nothing missed while offline (or
          deleted here) is left out."""
        days = self._keep_days()
        con.execute("UPDATE listings SET shared = 0 WHERE shared IS NULL AND uid IS NULL "
                    "AND COALESCE(last_seen, ts) >= ?", (mfm.utc_ago(days=days),))
        con.commit()
        while not self.stop_event.is_set() and self._send(con, changed_days=days):
            self._status(True, f"Catching up with the server… sent {self.sent:,}")
        while not self.stop_event.is_set() and self._send_megaphones(con):
            pass
        while not self.stop_event.is_set() and self._send_nicknames(con):
            pass
        url = self.server.url
        con.execute("DELETE FROM shared_state WHERE server IN (?, ?, ?)", (url, url + "#megaphones",
                                                                           url + "#nicknames"))
        con.commit()
        self._receive(con)
        self._receive_megaphones(con)
        self._receive_nicknames(con)

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
                mfm.ui_pause()
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
    def _send_megaphones(self, con) -> int:
        cols = ("id", "uid", "shared_sig", "ts", "player", "channel", "message", "kind", "color", "conf")
        rows = []
        for r in con.execute(f"SELECT {', '.join(cols)} FROM megaphones WHERE kind IS NOT NULL AND ts >= ? "
                             "ORDER BY id", (mfm.utc_ago(hours=MEGA_SERVER_HOURS),)):
            r = dict(zip(cols, r))
            if not r["uid"] or _mega_sig(r) != r["shared_sig"]:
                rows.append(r)
        if not rows:
            return 0
        rows = rows[:500]
        fresh = sum(1 for r in rows if not r["uid"])
        for r in rows:
            if not r["uid"]:
                r["uid"] = uuid.uuid4().hex
        res = self.server.send_megaphones([{k: r[k] for k in cols[3:] + ("uid",)} for r in rows])
        same = res.get("same", {})
        for r in rows:
            con.execute("UPDATE megaphones SET uid = ?, shared_sig = ? WHERE id = ?",
                        (same.get(r["uid"], r["uid"]), _mega_sig(r), r["id"]))
        con.commit()
        self.mega_sent += fresh
        return len(rows)

    def _receive_megaphones(self, con) -> None:
        key = self.server.url + "#megaphones"
        row = con.execute("SELECT seq FROM shared_state WHERE server = ?", (key,)).fetchone()
        seq = row[0] if row else 0
        hours = max(1, min(MEGA_SERVER_HOURS, float(self.cfg.get("megaphone_hours", 72) or 72)))
        new = 0
        while True:
            res = self.server.megaphone_changes(seq, hours)
            for m in res.get("megaphones", []):
                mfm.ui_pause()
                if con.execute("SELECT 1 FROM megaphones_deleted WHERE uid = ?", (m["uid"],)).fetchone():
                    continue                  # you deleted it here
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
        # work out the items and prices of new or better-read megaphones
        self.mega_received += new
        if mfm.update_offers(con) or new:
            self.on_megaphones(new)

    # -- nicknames (what players call items in megaphones)
    def _has_nicknames(self) -> bool:
        return "nicknames" in self.info       # servers before 2.2.0 don't keep them

    def _send_nicknames(self, con) -> int:
        if not self._has_nicknames():
            return 0
        rows = [r for r in con.execute("SELECT key, item, COALESCE(deleted, 0), updated, shared_sig FROM nicknames")
                if _nick_sig(r[1], r[2]) != r[4]][:500]
        if not rows:
            return 0
        # only real nicknames are shared. A "Not an item" mark (item '') stays here; it's
        # only sent, as a deletion, when it replaces a nickname that was shared before.
        def shared_before(sig):
            try:
                item, deleted = json.loads(sig or "null") or ("", 1)
            except ValueError:
                return False
            return bool(item) and not deleted
        send = [{"key": k, "item": i or "", "deleted": bool(d) or not i, "updated": u}
                for k, i, d, u, sig in rows if i or shared_before(sig)]
        if send:
            self.server.send_nicknames(send)
        for k, i, d, _, _ in rows:
            con.execute("UPDATE nicknames SET shared_sig = ? WHERE key = ?", (_nick_sig(i, d), k))
        con.commit()
        return len(rows)

    def _receive_nicknames(self, con) -> None:
        if not self._has_nicknames():
            return
        key = self.server.url + "#nicknames"
        row = con.execute("SELECT seq FROM shared_state WHERE server = ?", (key,)).fetchone()
        seq = row[0] if row else 0
        changed = 0
        while True:
            res = self.server.nickname_changes(seq)
            for n in res.get("nicknames", []):
                k, item, deleted = str(n.get("key") or ""), n.get("item") or "", 1 if n.get("deleted") else 0
                if not k:
                    continue
                sig = _nick_sig(item, deleted)
                local = con.execute("SELECT item, COALESCE(deleted, 0), updated, shared_sig FROM nicknames "
                                    "WHERE key = ?", (k,)).fetchone()
                if local:
                    if _nick_sig(local[0], local[1]) == sig or (deleted and not local[0] and not local[1]):
                        # (a shared nickname being deleted leaves a "Not an item" mark here as it is)
                        con.execute("UPDATE nicknames SET shared_sig = ? WHERE key = ?", (sig, k))
                        continue
                    unsent = _nick_sig(local[0], local[1]) != local[3]
                    if unsent and (local[2] or "") > (n.get("updated") or ""):
                        continue              # changed here more recently: ours gets sent
                    con.execute("UPDATE nicknames SET item = ?, deleted = ?, updated = ?, by = ?, shared_sig = ? "
                                "WHERE key = ?", (item, deleted, n.get("updated") or mfm.utc_now(), n.get("by"),
                                                  sig, k))
                else:
                    con.execute("INSERT INTO nicknames (key, item, deleted, added, by, updated, shared_sig) "
                                "VALUES (?,?,?,?,?,?,?)", (k, item, deleted, mfm.utc_now(), n.get("by"),
                                                           n.get("updated") or mfm.utc_now(), sig))
                changed += 1
            seq = res.get("seq", seq)
            con.execute("INSERT OR REPLACE INTO shared_state (server, seq) VALUES (?, ?)", (key, seq))
            con.commit()
            if not res.get("more"):
                break
        if changed and mfm.update_offers(con):
            self.on_megaphones(0)


def sign_in(url: str, username: str, password: str) -> dict:
    """Sign in and save the sign-in; returns the server's status (its name, and you)."""
    srv = Server(url)
    if not username.strip() or not password:
        raise SharedError("Enter your user name and password.")
    r = srv.login(username, password)
    save_login({"server": srv.url, "username": r["user"]["name"], "user_id": r["user"]["id"], "token": r["token"]})
    return srv.status()


def check_saved(url: str) -> dict:
    """Connect with the saved sign-in; returns the server's status."""
    login = load_login()
    if not login.get("token") or login.get("server") != normalize_url(url):
        raise SignedOut("Enter your password to sign in.")
    return Server(url, login["token"]).status()
