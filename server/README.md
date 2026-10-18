# Free Market Tracker server

A small self-hosted database that lets a group of players share prices. Everyone in
the group connects their Free Market Tracker to it (**Shared Database** in the app), and
each player's price sightings and megaphones show up for everyone within a few seconds.

- One person runs the server (on a PC, a home server, a NAS or a Raspberry Pi), makes an
  account for each player, and gives them the address, their user name and a password.
- Everything stored records which account sent it and from which IP address, and every
  sign-in is logged, so you can see if an account is used by someone it shouldn't be.
- It runs in Docker and uses **one TCP port: 8765**.
- Everything is stored in one SQLite file in a Docker volume.

## What you need

- A computer that stays on while people play, with [Docker](https://docs.docker.com/get-docker/)
  installed (Docker Desktop on Windows and macOS; Docker Engine on Linux). Any 64-bit PC
  works, and so does a Raspberry Pi 3 or newer.
- If players outside your home network will connect: access to your router's settings,
  to forward a port.

## Quick start

1. Copy the [`docker-compose.yml`](docker-compose.yml) file from this folder into a new
   folder on the server computer. Change `MFM_NAME` if you like.
2. In that folder, run:

   ```
   docker compose up -d
   ```

3. The first start makes an account called `admin`. Its password is in the log:

   ```
   docker compose logs mfm-server
   ```

   Look for `Account 'admin', password: …`.
4. Make an account for each player. It prints their first password:

   ```
   docker compose exec mfm-server mfm-server add-user Alice
   ```

5. Each player opens **Shared Database** in the app, enters the **server address**, their
   **user name** and **password**, and clicks **Connect**. The dot next to the button turns
   green. The app stays signed in (it keeps a sign-in token, not the password), and players
   can change their password there.

Check that it's running by opening `http://localhost:8765` in a browser on the server
computer. It says "Free Market Tracker server … is running."

Without Docker Compose:

```
docker volume create mfm-data
docker run -d --name mfm-server --restart unless-stopped -p 8765:8765 \
  -v mfm-data:/data -e MFM_NAME="Our Free Market" ghcr.io/jayee88/mfm-tracker-server:latest
docker exec mfm-server mfm-server add-user Alice
```

## Ports

| Port | Protocol | What it's for |
|---|---|---|
| **8765** | TCP | The app connects here (HTTP, or HTTPS if you set a certificate) |
| 80, 443 | TCP | Only with the optional HTTPS proxy (see below) |

To use another port, change the left side of the port mapping, e.g. `"9000:8765"`, and
use that port in the address (`203.0.113.5:9000`).

## The server address

Players enter `address:port` in the app, for example:

- On the same home network as the server: its local IP, e.g. `192.168.1.20:8765`. Find it
  with `ipconfig` (Windows), `ipconfig getifaddr en0` (macOS) or `hostname -I` (Linux).
- From the internet: your home's public IP, e.g. `203.0.113.5:8765`. Find it at
  [whatismyip.com](https://www.whatismyip.com/) on the server computer. Most home IPs
  change now and then; a free dynamic DNS name (e.g. from [Duck DNS](https://www.duckdns.org/)
  or [No-IP](https://www.noip.com/)) gives you a name that keeps working,
  e.g. `ourmarket.duckdns.org:8765`.
- With the HTTPS proxy: `https://prices.example.com`.

## Forwarding the port on your router

Players outside your home network need the router to pass port 8765 to the server
computer:

1. Give the server computer a fixed local IP: in the router, look for **DHCP
   reservation** (or "static lease") and reserve its current IP.
2. Find **Port forwarding** (sometimes under "NAT", "Virtual servers" or "Gaming").
3. Add a rule:
   - External / WAN port: **8765**
   - Internal / LAN IP: the server computer's IP, e.g. `192.168.1.20`
   - Internal port: **8765**
   - Protocol: **TCP**
4. Save. Test from outside your network (e.g. a phone on mobile data): open
   `http://YOUR-PUBLIC-IP:8765` in a browser.

Also allow the port in the server computer's firewall:

- **Windows:** Docker Desktop usually asks the first time. Otherwise: Windows Defender
  Firewall → Advanced settings → Inbound Rules → New Rule → Port → TCP 8765 → Allow.
- **Linux (ufw):** `sudo ufw allow 8765/tcp`
- **Linux (firewalld):** `sudo firewall-cmd --permanent --add-port=8765/tcp && sudo firewall-cmd --reload`

If your internet provider uses CGNAT (your router's WAN IP differs from your public IP),
port forwarding won't work. Use a VPN that everyone joins instead, such as
[Tailscale](https://tailscale.com/) or [ZeroTier](https://www.zerotier.com/), and the
server's VPN IP as the address. No port forwarding is needed then.

## Security

- Every player has their own account. Nothing can be read or sent without signing in.
- Passwords are stored as salted hashes (PBKDF2-SHA256), never as text. The app keeps a
  sign-in token, not the password; a token lasts 90 days without use
  (`MFM_SESSION_DAYS`).
- Every sighting and megaphone records the account (its name and unique id) and the IP
  address it came from, both when it was added and when it was last changed.
- Every account's IP addresses are kept (first and last time, number of requests), and
  sign-ins, failed sign-ins, password changes and account changes are logged. See them
  with `user-info NAME` and `log`. A first use from a new IP address is logged too.
- 10 failed sign-ins from one IP address within 15 minutes block it for 15 minutes.
- If an account was misused: `disable-user NAME` (blocks it and signs it out everywhere),
  then `reset-password NAME` and `enable-user NAME` to give it back.
- Plain HTTP sends passwords and tokens unencrypted. That's fine on your home network or
  over a VPN. Over the internet, use HTTPS (below).
- Only price sightings, megaphones and nicknames are stored: item, price, shop, player
  name, map, channel, times, notes, megaphone messages and item nicknames, plus who sent
  them and from where.

## HTTPS (optional)

**With a domain name: the Caddy proxy (recommended).** Caddy gets a free certificate
from Let's Encrypt automatically. Point your domain (or a dynamic DNS name) at your public
IP, forward ports **80** and **443** (TCP) instead of 8765, and use this
`docker-compose.yml`:

```yaml
services:
  mfm-server:
    image: ghcr.io/jayee88/mfm-tracker-server:latest
    restart: unless-stopped
    environment:
      MFM_NAME: "Our Free Market"
      MFM_TRUST_PROXY: "1"         # log the players' IPs that Caddy passes on
    volumes:
      - mfm-data:/data
  caddy:
    image: caddy:2
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    command: caddy reverse-proxy --from prices.example.com --to mfm-server:8765
    volumes:
      - caddy-data:/data
volumes:
  mfm-data:
  caddy-data:
```

Players then enter `https://prices.example.com` as the address.

**With your own certificate:** mount the certificate files and set `MFM_TLS_CERT` and
`MFM_TLS_KEY` (see the commented lines in `docker-compose.yml`). The address then starts
with `https://`, e.g. `https://ourmarket.duckdns.org:8765`. The certificate has to be a
real one (e.g. from Let's Encrypt): the app doesn't accept self-signed certificates.

## Settings

Set these under `environment:` in `docker-compose.yml`, then run `docker compose up -d`
again.

| Setting | Default | What it does |
|---|---|---|
| `MFM_NAME` | Shared prices | the server's name, shown in the app |
| `MFM_PORT` | 8765 | the port inside the container |
| `MFM_KEEP_DAYS` | 30 | sightings not seen for this many days are deleted (0 = keep all) |
| `MFM_MEGAPHONE_HOURS` | 72 | megaphones are kept this many hours (each player still sees only the hours set in their app) |
| `MFM_TLS_CERT`, `MFM_TLS_KEY` | (none) | certificate and key files (PEM) for HTTPS |
| `MFM_SESSION_DAYS` | 90 | a sign-in ends after this many days without use |
| `MFM_TRUST_PROXY` | (off) | `1` = take players' IPs from the `X-Forwarded-For` header; only behind your own reverse proxy (e.g. Caddy), or anyone could fake their IP |
| `MFM_DATA` | /data | where the database is kept inside the container |

## Commands

Run these on the server computer, in the folder with `docker-compose.yml`:

| Command | What it does |
|---|---|
| `docker compose exec mfm-server mfm-server add-user NAME` | make an account; prints its first password |
| `docker compose exec mfm-server mfm-server list-users` | all accounts: status, last seen, last IP |
| `docker compose exec mfm-server mfm-server user-info NAME` | an account's IP addresses, sign-ins and recent events |
| `docker compose exec mfm-server mfm-server log 100` | the last 100 sign-ins, failed sign-ins and account changes |
| `docker compose exec mfm-server mfm-server reset-password NAME` | a new password (signs them out everywhere) |
| `docker compose exec mfm-server mfm-server disable-user NAME` | block an account and sign it out (`enable-user` undoes it) |
| `docker compose exec mfm-server mfm-server logout-user NAME` | sign an account out everywhere |
| `docker compose exec mfm-server mfm-server remove-user NAME` | delete an account (what it sent stays, with its name and id) |
| `docker compose exec mfm-server mfm-server stats` | how much is stored, and from whom |
| `docker compose logs -f mfm-server` | the server's log |
| `docker compose pull && docker compose up -d` | update to the latest version |
| `docker compose down` | stop it (the data stays) |

## Backups

The database is the file `mfm-server.db` in the `mfm-data` volume. To copy it out:

```
docker compose exec mfm-server sh -c "python -c \"import sqlite3; s=sqlite3.connect('/data/mfm-server.db'); s.backup(sqlite3.connect('/data/backup.db'))\""
docker compose cp mfm-server:/data/backup.db ./mfm-server-backup.db
```

To restore, stop the server, copy the file back as `/data/mfm-server.db`
(`docker compose cp ./mfm-server-backup.db mfm-server:/data/mfm-server.db`), and start it.

## Troubleshooting

- **The app says "Can't reach the server":** check the address and port; open
  `http://ADDRESS:8765` in a browser on the player's computer. On the same network it
  should work right away. From outside, check the port forwarding and the firewall.
- **"Wrong user name or password":** check them, or make a new password with
  `reset-password NAME`. User names aren't case-sensitive; passwords are.
- **"Your sign-in has ended":** the password was changed or reset, the account was
  disabled or signed out, or it wasn't used for 90 days. Enter the password and connect.
- **"Too many failed sign-ins":** wait 15 minutes.
- **It works at home but not from outside:** your router may not support connecting to
  your own public IP from inside ("NAT loopback"). Use the local IP at home and the public
  address elsewhere, or use a VPN like Tailscale.

## Building the image yourself

```
cd server
docker build -t mfm-tracker-server .
```

Or run it without Docker (Python 3.10 or newer, no other packages):

```
python mfm_server.py serve
```

## For developers: the API

JSON over HTTP. Sign in with `POST /api/v1/login`; every other `/api` request needs
`Authorization: Bearer <token>`.

| Request | Answer |
|---|---|
| `GET /health` | plain text, no sign-in needed |
| `POST /api/v1/login` with `{"username", "password"}` | `{"token", "user": {"id", "name"}, "expires"}` |
| `POST /api/v1/logout` | ends this token |
| `POST /api/v1/password` with `{"password", "new_password"}` | changes it; signs out your other devices |
| `GET /api/v1/status` | `{"name", "version", "sightings", "megaphones", "nicknames", "seq", "you": {"id", "name"}, "keep_days", "megaphone_hours"}` |
| `POST /api/v1/sightings` with `{"sightings": [...]}` (up to 500) | `{"seq", "same": {sent uid: stored uid}}` |
| `GET /api/v1/sightings?since=SEQ&limit=N` | `{"sightings": [...], "seq", "more"}` |
| `POST /api/v1/megaphones` with `{"megaphones": [...]}` (up to 500) | `{"seq", "same": {sent uid: stored uid}}` |
| `GET /api/v1/megaphones?since=SEQ&hours=H` | `{"megaphones": [...], "seq", "more"}` (only the last H hours) |
| `POST /api/v1/nicknames` with `{"nicknames": [{key, item, deleted, updated}]}` (up to 500) | `{"seq", "same": {}}`; the newest change of each nickname wins; item `""` = "not an item" |
| `GET /api/v1/nicknames?since=SEQ` | `{"nicknames": [{key, item, deleted, updated, seq, by}], "seq", "more"}` |

A sighting is `{uid, ts, item, price, qty, shop, seller, map, channel, sold, sold_ts,
last_seen, notes}`, with times in UTC (`2026-10-17T20:00:00Z`). Every new or changed
sighting gets the next `seq` number; clients ask for everything after the last one they
have. A listing sent by two players (same item, price and shop within a day) is stored
once; `same` tells the sender which stored sighting theirs became. Once sold, a sighting
stays sold.

A megaphone is `{uid, ts, player, channel, message, kind, color, conf}`, where `conf` is
how sure the sender's OCR was (0-100). Reads within two minutes of each other with nearly
the same message, and the same player (allowing for look-alike letters) or channel, are
one megaphone: the read with the highest `conf` is kept.
