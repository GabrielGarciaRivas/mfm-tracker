"""Writes mfm_google_client.py (the app's Google sign-in client for the Shared
Database) from the GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET environment variables.
Google treats a desktop app's client secret as not secret; it only identifies the app."""
import os
from pathlib import Path

cid = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
sec = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
Path(__file__).resolve().parents[2].joinpath("mfm_google_client.py").write_text(
    f"CLIENT_ID = {cid!r}\nCLIENT_SECRET = {sec!r}\n", encoding="utf-8")
print("Google sign-in:", "built in" if cid else "not set (add the GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET secrets)")
