"""Shared Database: price sightings kept in sync with a Google spreadsheet, so a group
of players who can all edit the same sheet see each other's prices.

- Sign-in is Google's own (OAuth for desktop apps): the browser opens Google's page,
  you allow access to your spreadsheets, and the app gets a token it keeps in the
  data folder. Nothing else is stored, and only the spreadsheet you give it is used.
- The sheet gets a tab "Prices" with one row per sighting. New sightings of items
  in the item list are added to it; sightings that change (sold, seen again, a
  note) are updated in place; everyone's rows are copied into the local prices.
- Names that end up in Review are only uploaded once they're matched to an item.

Local bookkeeping lives in prices.db, in columns of `listings`:
  uid         the sighting's id in the sheet (shared by everyone)
  shared      NULL = local only, 0 = to upload, 1 = in the sheet
  shared_row  its row in the sheet
  shared_sig  what its values were when last synced (a change means: update the sheet)
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta

import mfm

SCOPES = "https://www.googleapis.com/auth/spreadsheets openid email"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
TOKEN_PATH = mfm.SETTINGS_DIR / "google_token.json"
CLIENT_PATH = mfm.SETTINGS_DIR / "google_client.json"
TAB = "Prices"
HEADER = ["ID", "Time (UTC)", "Item", "Price", "Qty", "Shop", "Player", "Map", "Channel", "Sold",
          "Sold time (UTC)", "Last seen (UTC)", "Notes", "Added by"]
LAST_COL = "N"
FIELDS = ("item", "price", "qty", "shop", "seller", "map", "channel", "sold", "sold_ts", "last_seen", "notes")


class SharedError(Exception):
    """Something the user can act on (no access, not signed in, no internet ...)."""


# --------------------------------------------------------------------------- set-up

def sheet_id(url: str) -> str | None:
    """The spreadsheet's id from its link (or the id itself)."""
    url = (url or "").strip()
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]{20,})", url)
    if m:
        return m.group(1)
    return url if re.fullmatch(r"[A-Za-z0-9_-]{25,}", url) else None


def client() -> tuple[str, str] | None:
    """The app's Google sign-in client (id, secret): your own from the data folder,
    else the one built into the app, else MFM_GOOGLE_CLIENT_ID/SECRET."""
    try:
        d = json.loads(CLIENT_PATH.read_text())
        if d.get("client_id"):
            return d["client_id"], d.get("client_secret", "")
    except (OSError, ValueError):
        pass
    try:
        import mfm_google_client as g     # written into the app when it's built
        if getattr(g, "CLIENT_ID", ""):
            return g.CLIENT_ID, getattr(g, "CLIENT_SECRET", "")
    except ImportError:
        pass
    cid = os.environ.get("MFM_GOOGLE_CLIENT_ID")
    return (cid, os.environ.get("MFM_GOOGLE_CLIENT_SECRET", "")) if cid else None


def save_client(client_id: str, client_secret: str) -> None:
    mfm.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    CLIENT_PATH.write_text(json.dumps({"client_id": client_id.strip(), "client_secret": client_secret.strip()},
                                      indent=2))


def load_token() -> dict:
    try:
        return json.loads(TOKEN_PATH.read_text())
    except (OSError, ValueError):
        return {}


def save_token(tok: dict) -> None:
    mfm.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(tok, indent=2))
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except OSError:
        pass


def sign_out() -> None:
    tok = load_token()
    if tok.get("refresh_token"):
        try:
            _post("https://oauth2.googleapis.com/revoke", {"token": tok["refresh_token"]})
        except Exception:
            pass
    TOKEN_PATH.unlink(missing_ok=True)


def _post(url: str, form: dict) -> dict:
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": mfm.USER_AGENT,
                                                          "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=mfm.ssl_context()) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read() or b"{}")
        except ValueError:
            body = {}
        raise SharedError(body.get("error_description") or body.get("error") or f"HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise SharedError(f"Can't reach Google: {e.reason}") from None


def sign_in(open_browser, cancelled: threading.Event | None = None, timeout: float = 300) -> dict:
    """Google's sign-in for desktop apps: a page opens in the browser (open_browser(url)),
    and Google sends the answer back to a one-time address on this computer.
    Returns the saved token (with the account's email)."""
    import http.server

    cl = client()
    if not cl:
        raise SharedError("This copy of the app has no Google sign-in set up.")
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(16)
    got: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] != state:
                self.send_response(404)
                self.end_headers()
                return
            got.update({k: v[0] for k, v in q.items()})
            ok = "code" in got
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = ("Signed in. You can close this tab and go back to Free Market Tracker." if ok else
                   "Sign-in was cancelled. You can close this tab.")
            self.wfile.write(f"<html><body style='font-family:sans-serif;padding:40px'><h2>{msg}</h2>"
                             "</body></html>".encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 0.5
    redirect = f"http://127.0.0.1:{server.server_port}"
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": cl[0], "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
        "access_type": "offline", "prompt": "consent"})
    open_browser(url)
    end = time.monotonic() + timeout
    try:
        while "code" not in got and "error" not in got:
            if time.monotonic() > end or (cancelled is not None and cancelled.is_set()):
                raise SharedError("Sign-in was cancelled.")
            server.handle_request()
    finally:
        server.server_close()
    if "error" in got:
        raise SharedError("Sign-in was cancelled." if got["error"] == "access_denied" else got["error"])
    tok = _post(TOKEN_URL, {"code": got["code"], "client_id": cl[0], "client_secret": cl[1],
                            "redirect_uri": redirect, "grant_type": "authorization_code",
                            "code_verifier": verifier})
    if not tok.get("refresh_token"):
        raise SharedError("Google didn't allow offline access; try again.")
    email = ""
    try:
        payload = tok["id_token"].split(".")[1]
        email = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("email", "")
    except Exception:
        pass
    saved = {"refresh_token": tok["refresh_token"], "email": email, "client_id": cl[0],
             "access_token": tok.get("access_token"), "expires": time.time() + int(tok.get("expires_in", 0)) - 60}
    save_token(saved)
    return saved


# --------------------------------------------------------------------------- the sheet

class Sheet:
    """The Google Sheets API for one spreadsheet, as the signed-in user."""

    def __init__(self, spreadsheet_id: str):
        self.id = spreadsheet_id
        self.tok = load_token()
        if not self.tok.get("refresh_token"):
            raise SharedError("Not signed in to Google.")

    def _access(self) -> str:
        if self.tok.get("access_token") and time.time() < self.tok.get("expires", 0):
            return self.tok["access_token"]
        cl = client()
        if not cl:
            raise SharedError("This copy of the app has no Google sign-in set up.")
        try:
            r = _post(TOKEN_URL, {"refresh_token": self.tok["refresh_token"], "client_id": cl[0],
                                  "client_secret": cl[1], "grant_type": "refresh_token"})
        except SharedError as e:
            if "invalid_grant" in str(e) or "expired" in str(e).lower() or "revoked" in str(e).lower():
                raise SharedError("Your Google sign-in has expired: sign in again.") from None
            raise
        self.tok.update(access_token=r["access_token"], expires=time.time() + int(r.get("expires_in", 3600)) - 60)
        save_token(self.tok)
        return self.tok["access_token"]

    def call(self, method: str, path: str, body=None, query=None):
        url = f"{SHEETS}/{self.id}{path}" + ("?" + urllib.parse.urlencode(query, doseq=True) if query else "")
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(3):
            req = urllib.request.Request(url, data=data, method=method, headers={
                "Authorization": f"Bearer {self._access()}", "User-Agent": mfm.USER_AGENT,
                "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60, context=mfm.ssl_context()) as r:
                    return json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                try:
                    msg = json.loads(e.read() or b"{}").get("error", {}).get("message", "")
                except ValueError:
                    msg = ""
                if e.code == 401 and attempt == 0:
                    self.tok["expires"] = 0          # get a fresh access token and retry
                    continue
                if e.code == 429 or e.code >= 500:
                    time.sleep(5 * (attempt + 1))  # too many requests / Google busy: wait
                    continue
                if e.code == 403:
                    raise SharedError("You don't have access to this spreadsheet. Ask its owner to share "
                                      "it with your Google account as an editor.") from None
                if e.code == 404:
                    raise SharedError("Spreadsheet not found: check the link.") from None
                raise SharedError(msg or f"Google Sheets error {e.code}") from None
            except urllib.error.URLError as e:
                raise SharedError(f"Can't reach Google: {e.reason}") from None
        raise SharedError("Google Sheets is busy; trying again soon.")

    def title(self) -> str:
        return self.call("GET", "", query={"fields": "properties.title"})["properties"]["title"]

    def ensure_tab(self) -> None:
        """The Prices tab with its header row; writing the header also checks that you
        can edit the sheet."""
        info = self.call("GET", "", query={"fields": "sheets.properties.title"})
        if TAB not in [s["properties"]["title"] for s in info.get("sheets", [])]:
            self.call("POST", ":batchUpdate", {"requests": [{"addSheet": {"properties": {
                "title": TAB, "gridProperties": {"frozenRowCount": 1}}}}]})
        self.call("PUT", f"/values/{TAB}!A1:{LAST_COL}1", {"values": [HEADER]},
                  {"valueInputOption": "RAW"})

    def rows(self, first: int = 2) -> list[list]:
        """Rows from row `first` down (row 1 is the header)."""
        r = self.call("GET", f"/values/{TAB}!A{first}:{LAST_COL}",
                      query={"valueRenderOption": "UNFORMATTED_VALUE", "majorDimension": "ROWS"})
        return r.get("values", [])

    def append(self, rows: list[list]) -> int:
        """Add rows at the end; returns the sheet row of the first one."""
        r = self.call("POST", f"/values/{TAB}!A1:{LAST_COL}1:append", {"values": rows},
                      {"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"})
        rng = r.get("updates", {}).get("updatedRange", "")
        m = re.search(r"!A(\d+)", rng)
        if not m:
            raise SharedError("Unexpected answer from Google Sheets.")
        return int(m.group(1))

    def update(self, rows: dict[int, list]) -> None:
        if rows:
            self.call("POST", "/values:batchUpdate", {"valueInputOption": "RAW", "data": [
                {"range": f"{TAB}!A{n}:{LAST_COL}{n}", "values": [v]} for n, v in rows.items()]})


# --------------------------------------------------------------------------- local side

def prepare(con) -> None:
    """Bookkeeping in prices.db (the listings columns are added by mfm.db())."""
    con.execute("CREATE INDEX IF NOT EXISTS idx_listings_uid ON listings(uid)")
    con.execute("CREATE TABLE IF NOT EXISTS shared_skip (uid TEXT PRIMARY KEY)")
    con.commit()


def _cell(v):
    return "" if v is None else v


def _row_values(r: dict, uid: str, by: str) -> list:
    return [uid, r["ts"], r["item"], r["price"], r["qty"] or 1, _cell(r["shop"]), _cell(r["seller"]),
            _cell(r["map"]), _cell(r["channel"]), 1 if r["sold"] else 0, _cell(r["sold_ts"]),
            _cell(r["last_seen"]), _cell(r["notes"]), by]


def _sig(r: dict) -> str:
    return json.dumps([("" if r[f] is None else str(r[f])) for f in FIELDS])


def _from_sheet(v: list) -> dict | None:
    v = list(v) + [""] * (len(HEADER) - len(v))
    uid, ts, item = str(v[0]).strip(), str(v[1]).strip(), str(v[2]).strip()
    try:
        price = int(float(str(v[3]).replace(",", "")))
        qty = int(float(str(v[4] or 1).replace(",", "")))
    except ValueError:
        return None
    if not uid or not item or not ts.endswith("Z") or price <= 0:
        return None
    s = lambda x: (str(x).strip() or None) if x not in (None, "") else None
    sold = str(v[9]).strip().lower() in ("1", "true", "yes", "sold")
    return {"uid": uid, "ts": ts, "item": item, "price": price, "qty": qty, "shop": s(v[5]), "seller": s(v[6]),
            "map": s(v[7]), "channel": s(v[8]), "sold": int(sold), "sold_ts": s(v[10]),
            "last_seen": s(v[11]) or ts, "notes": s(v[12]), "by": s(v[13])}


def _same_listing(con, r: dict, hours: int = 24) -> int | None:
    """A local sighting that is this one (same item, price, player or shop, and map,
    within a day), for when two people logged the same listing."""
    try:
        t = datetime.strptime(r["ts"], mfm.UTC_FMT)
    except ValueError:
        return None
    lo, hi = ((t + timedelta(hours=d)).strftime(mfm.UTC_FMT) for d in (-hours, hours))
    for rid, title, seller, mp in con.execute(
            "SELECT id, shop, seller, map FROM listings WHERE item = ? AND price = ? AND ts BETWEEN ? AND ?",
            (r["item"], r["price"], lo, hi)):
        if mfm._same_shop(title, seller, mp, r["shop"] or "", r["seller"] or "", r["map"] or ""):
            return rid
    return None


class SharedSync:
    """Keeps prices.db and the shared sheet in step, in a background thread.

    Every few seconds: new sightings (of items in the item list) are added to the
    sheet, and changed ones updated. Every 15 seconds the rows other people added
    are copied in; every 2 minutes the whole sheet is read again for their changes.
    `on_status(dict)` hears how it's going: {"ok": bool, "text": str, ...}."""

    UPLOAD_EVERY, NEW_ROWS_EVERY, ALL_ROWS_EVERY = 4.0, 15.0, 120.0

    def __init__(self, cfg: dict, spreadsheet_id: str, on_status=lambda s: None, on_new_rows=lambda n: None):
        self.cfg, self.id = cfg, spreadsheet_id
        self.on_status, self.on_new_rows = on_status, on_new_rows
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.thread: threading.Thread | None = None
        self.known_rows = 1           # rows of the sheet copied in so far (1 = header)
        self.uploaded = self.downloaded = 0
        self.ok = False
        self.last_ok = 0.0
        self.force_full = False
        self.by = ""

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.wake.set()
        mfm.SHARE_NEW = False

    def _status(self, ok: bool, text: str) -> None:
        self.ok = ok
        if ok:
            self.last_ok = time.monotonic()
        self.on_status({"ok": ok, "text": text, "uploaded": self.uploaded, "downloaded": self.downloaded})

    def _run(self) -> None:
        con = mfm.db()
        prepare(con)
        sheet = None
        next_new = next_all = 0.0
        while not self.stop_event.is_set():
            try:
                if sheet is None:
                    sheet = Sheet(self.id)
                    sheet.ensure_tab()
                    self.by = load_token().get("email", "")
                    mfm.SHARE_NEW = True
                now = time.monotonic()
                if now >= next_all or self.force_full:
                    self.force_full = False
                    self._download(con, sheet, full=True)
                    next_all = now + self.ALL_ROWS_EVERY
                    next_new = now + self.NEW_ROWS_EVERY
                elif now >= next_new:
                    self._download(con, sheet, full=False)
                    next_new = now + self.NEW_ROWS_EVERY
                self._upload(con, sheet)
                self._push_changes(con, sheet)
                self._status(True, "Connected")
            except SharedError as e:
                self._status(False, str(e))
                if "access" in str(e) or "sign" in str(e).lower() or "not found" in str(e):
                    sheet = None
                    self.stop_event.wait(30)
                    continue
            except Exception as e:
                self._status(False, f"{type(e).__name__}: {e}")
            self.wake.wait(self.UPLOAD_EVERY)
            self.wake.clear()
        con.close()

    # -- sheet -> local
    def _download(self, con, sheet: Sheet, full: bool) -> None:
        first = 2 if full else self.known_rows + 1
        rows = sheet.rows(first)
        keep_days = self.cfg.get("keep_days", 30) if self.cfg.get("retention", "archive") != "keep" else None
        oldest = mfm.utc_ago(days=keep_days) if keep_days else ""
        has_list = mfm.has_item_list()
        skip = {u for (u,) in con.execute("SELECT uid FROM shared_skip")}
        new = 0
        for i, v in enumerate(rows):
            n = first + i
            r = _from_sheet(v)
            if not r or r["uid"] in skip:
                continue
            if oldest and (r["last_seen"] or r["ts"]) < oldest:
                continue                      # older than you keep prices for
            if has_list and not mfm.is_known_item(r["item"]):
                continue                      # someone typed something into the sheet
            local = con.execute("SELECT id, shared_sig FROM listings WHERE uid = ?", (r["uid"],)).fetchone()
            sig = _sig(r)
            if local:
                rid, old_sig = local
                if old_sig != sig:            # changed in the sheet: take it
                    con.execute("UPDATE listings SET item=?, price=?, qty=?, shop=?, seller=?, map=?, channel=?, "
                                "sold=?, sold_ts=?, last_seen=?, notes=?, shared=1, shared_row=?, shared_sig=? "
                                "WHERE id=?", tuple(r[f] for f in FIELDS) + (n, sig, rid))
                else:
                    con.execute("UPDATE listings SET shared_row = ? WHERE id = ?", (n, rid))
                continue
            same = _same_listing(con, r)
            if same:
                srow = con.execute("SELECT uid FROM listings WHERE id = ?", (same,)).fetchone()
                if srow and srow[0]:          # two people uploaded the same listing: ignore this one
                    con.execute("INSERT OR IGNORE INTO shared_skip (uid) VALUES (?)", (r["uid"],))
                else:                         # yours, not uploaded yet: it's this row
                    con.execute("UPDATE listings SET uid=?, shared=1, shared_row=?, shared_sig=? WHERE id=?",
                                (r["uid"], n, sig, same))
                continue
            con.execute(
                "INSERT INTO listings (ts, item, price, qty, shop, seller, map, channel, raw, session, sold, "
                "last_seen, sold_ts, notes, uid, shared, shared_row, shared_sig) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
                (r["ts"], r["item"], r["price"], r["qty"], r["shop"], r["seller"], r["map"], r["channel"],
                 f"shared by {r['by'] or 'someone'}", "shared", r["sold"], r["last_seen"], r["sold_ts"],
                 r["notes"], r["uid"], n, sig))
            new += 1
        con.commit()
        self.known_rows = first + len(rows) - 1 if full else max(self.known_rows, first + len(rows) - 1)
        if new:
            self.downloaded += new
            self.on_new_rows(new)

    # -- local -> sheet
    def _upload(self, con, sheet: Sheet) -> None:
        if not mfm.has_item_list():
            return                            # can't tell real items from misreads
        # names still in Review wait (they're uploaded once matched to an item)
        ids = [rid for rid, item in con.execute("SELECT id, item FROM listings WHERE shared = 0 ORDER BY id")
               if mfm.is_known_item(item)][:200]
        if not ids:
            return
        cur = con.execute("SELECT id, ts, item, price, qty, shop, seller, map, channel, sold, sold_ts, last_seen, "
                          f"notes FROM listings WHERE id IN ({','.join('?' * len(ids))}) ORDER BY id", ids)
        names = [d[0] for d in cur.description]
        todo = [dict(zip(names, row)) for row in cur.fetchall()]
        uids = [uuid.uuid4().hex[:16] for _ in todo]
        first = sheet.append([_row_values(r, u, self.by) for r, u in zip(todo, uids)])
        for i, (r, u) in enumerate(zip(todo, uids)):
            con.execute("UPDATE listings SET uid=?, shared=1, shared_row=?, shared_sig=? WHERE id=?",
                        (u, first + i, _sig(r), r["id"]))
        con.commit()
        self.uploaded += len(todo)
        self.known_rows = max(self.known_rows, first + len(todo) - 1)

    def _push_changes(self, con, sheet: Sheet) -> None:
        cur = con.execute("SELECT id, uid, shared_row, shared_sig, ts, item, price, qty, shop, seller, map, channel, "
                          "sold, sold_ts, last_seen, notes, raw FROM listings WHERE shared = 1 AND shared_row "
                          "IS NOT NULL AND COALESCE(last_seen, ts) >= ?", (mfm.utc_ago(days=7),))
        names = [d[0] for d in cur.description]
        changed = {}
        for row in cur.fetchall():
            r = dict(zip(names, row))
            sig = _sig(r)
            if sig != r["shared_sig"]:
                by = (r["raw"] or "")[len("shared by "):] if (r["raw"] or "").startswith("shared by ") else self.by
                changed[r["shared_row"]] = (r["id"], sig, _row_values(r, r["uid"], by))
        if not changed:
            return
        items = list(changed.items())[:100]
        # the rows must still be where they were (someone may have sorted or deleted rows)
        got = sheet.call("GET", "/values:batchGet", query=[("ranges", f"{TAB}!A{n}") for n, _ in items]
                         + [("valueRenderOption", "UNFORMATTED_VALUE")])
        found = [str((vr.get("values") or [[""]])[0][0]) for vr in got.get("valueRanges", [])]
        moved = [n for (n, v), uid in zip(items, found) if uid != v[2][0]]
        if moved or len(found) != len(items):
            self.force_full = True            # read the whole sheet again first
            return
        sheet.update({n: v[2] for n, v in items})
        for n, (rid, sig, _) in items:
            con.execute("UPDATE listings SET shared_sig = ? WHERE id = ?", (sig, rid))
        con.commit()


def connect(spreadsheet_id: str) -> str:
    """Check the sheet can be used (you're signed in, can open and edit it); returns
    its title."""
    sheet = Sheet(spreadsheet_id)
    title = sheet.title()
    sheet.ensure_tab()
    return title
