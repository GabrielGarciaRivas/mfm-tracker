"""Checks the app's self-update (mfm.download_update / install_update / start_new_app)
on this system, with the newest GitHub release: a stand-in for the running app is
started, the release is downloaded and swapped in while it runs, the new app's
OCR self-test is run, and the new app is started on its own.

    python tests/update_check.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("XDG_DATA_HOME", tempfile.mkdtemp())
import mfm  # noqa: E402

if os.environ.get("GITHUB_TOKEN"):
    # shared CI machines run into GitHub's limit for anonymous API calls
    import urllib.request

    def _get(url, timeout=30):
        req = urllib.request.Request(url, headers={"User-Agent": mfm.USER_AGENT,
                                                   "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"]})
        with urllib.request.urlopen(req, timeout=timeout, context=mfm.ssl_context()) as r:
            return r.read()
    mfm._get = _get


def running(name_part: str, but: int) -> bool:
    """Is a process with name_part in its command line running, other than pid `but`?"""
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
        return any(name_part in line and f'"{but}"' not in line for line in out.splitlines())
    out = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    return any(name_part in line and line.split()[0] != str(but) for line in out.splitlines())


def main() -> int:
    info = mfm.latest_release()
    print("latest:", info["version"], info["asset_name"], info["size"], info["digest"][:20])
    assert info["asset_url"], "no download for this system"

    home = Path(tempfile.mkdtemp(prefix="mfm upd "))       # a space in the path, like real installs
    stand_in = shutil.which("ping" if sys.platform == "win32" else "sleep")
    if sys.platform == "darwin":
        exe = home / "Free Market Tracker.app" / "Contents" / "MacOS" / "Free Market Tracker"
    elif sys.platform == "win32":
        exe = home / "Free Market Tracker.exe"
    else:
        exe = home / "Free Market Tracker"
    exe.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(stand_in, exe)      # (not copy2: macOS won't copy a system file's flags)
    exe.chmod(0o755)
    args = ["-n", "300", "127.0.0.1"] if sys.platform == "win32" else ["300"]
    old_proc = subprocess.Popen([str(exe)] + args, stdout=subprocess.DEVNULL)
    time.sleep(1)
    assert old_proc.poll() is None, "the stand-in app isn't running"

    mfm.FROZEN = True
    sys.executable = str(exe)
    print("target:", mfm.update_target(), "blocker:", mfm.update_blocker())
    assert mfm.update_blocker() is None

    t = time.time()
    seen = []
    path = mfm.download_update(info, progress=lambda d, n: seen.append((d, n)))
    print(f"downloaded {seen[-1][0]:,} bytes in {time.time() - t:.1f}s (SHA-256 checked)")
    cmd = mfm.install_update(path)
    target = mfm.update_target()
    print("installed; start command:", cmd)
    print("folder now:", sorted(os.listdir(target.parent)))
    assert target.exists() and Path(str(target) + ".old").exists()
    assert not (target.parent / ".mfm-update").exists()
    assert old_proc.poll() is None, "the running app was stopped by the swap"

    new_exe = target / "Contents" / "MacOS" / "Free Market Tracker" if sys.platform == "darwin" else target
    r = subprocess.run([str(new_exe), "selftest"], capture_output=True, text=True, timeout=600)
    print("selftest:", r.returncode, (r.stdout + r.stderr).strip()[-300:])
    assert r.returncode == 0, "the new app's self-test failed"
    if sys.platform == "darwin":
        r = subprocess.run(["codesign", "--verify", "--deep", str(target)], capture_output=True, text=True)
        print("codesign --verify:", r.returncode, r.stderr.strip())
        assert r.returncode == 0

    mfm.start_new_app(cmd)
    time.sleep(20)
    started = running("Free Market Tracker.exe" if sys.platform == "win32" else str(new_exe), old_proc.pid)
    print("new app running on its own:", started)
    assert started, "the new app didn't start"
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/IM", "Free Market Tracker.exe"], capture_output=True)
    else:
        subprocess.run(["pkill", "-f", str(new_exe)], capture_output=True)

    old_proc.kill()
    old_proc.wait()
    time.sleep(1)
    mfm.cleanup_old_update()
    assert not Path(str(target) + ".old").exists(), "the old app wasn't cleaned up"
    print("old app removed")
    print(f"update check passed on {mfm.update_platform()} ({info['version']})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f"FAILED at line {tb.lineno} ({tb.line}): {type(e).__name__}: {e}")
        sys.exit(1)
