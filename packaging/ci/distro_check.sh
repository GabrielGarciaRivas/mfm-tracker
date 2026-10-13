#!/bin/sh
# Checks the Linux install instructions in README.md on one distro, inside its
# container (run by .github/workflows/distro-check.yml):
#   1. installs the packages the README lists for this distro family,
#   2. runs from source: venv + requirements, OCR selftest, GUI start under Xvfb,
#   3. runs the released app (if APP is given): OCR selftest, GUI start,
#   4. reports which Wayland screenshot tools the distro packages.
# Usage: distro_check.sh FAMILY [APP]     (run from the repository root)
set -u
FAMILY="$1"
APP="${2:-}"
PY=python3
WAYLAND_TOOLS=""
say() { printf '\n== %s\n' "$*"; }

say "install ($FAMILY)"
case "$FAMILY" in
  apt)        # Debian, Ubuntu, Linux Mint, Pop!_OS, elementary OS, Zorin OS
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-tk tesseract-ocr tesseract-ocr-eng \
      xvfb >/dev/null || exit 1
    for t in grim kde-spectacle gnome-screenshot; do
      apt-cache show "$t" >/dev/null 2>&1 && WAYLAND_TOOLS="$WAYLAND_TOOLS $t"
    done ;;
  dnf)        # Fedora
    dnf install -y -q python3 python3-tkinter tesseract tesseract-langpack-eng \
      xorg-x11-server-Xvfb findutils >/dev/null || exit 1
    for t in grim spectacle gnome-screenshot; do
      dnf info -q "$t" >/dev/null 2>&1 && WAYLAND_TOOLS="$WAYLAND_TOOLS $t"
    done ;;
  el)         # RHEL, Rocky Linux, AlmaLinux 9 / 10 (Tesseract is in EPEL)
    dnf install -y -q epel-release >/dev/null || exit 1
    if [ "$(rpm -E %rhel)" -ge 10 ]; then
      dnf install -y -q python3 python3-tkinter tesseract tesseract-langpack-eng >/dev/null || exit 1
      dnf install -y -q /usr/bin/Xvfb >/dev/null 2>&1     # only for this check's GUI test
    else
      dnf config-manager --set-enabled crb >/dev/null 2>&1
      dnf install -y -q python3.12 python3.12-tkinter tesseract tesseract-langpack-eng \
        xorg-x11-server-Xvfb >/dev/null || exit 1
      PY=python3.12
    fi
    for t in grim spectacle gnome-screenshot; do
      dnf info -q "$t" >/dev/null 2>&1 && WAYLAND_TOOLS="$WAYLAND_TOOLS $t"
    done ;;
  zypper)     # openSUSE Tumbleweed / Leap
    if grep -q 'VERSION_ID="15' /etc/os-release; then
      zypper -n -q install python311 python311-tk tesseract-ocr \
        tesseract-ocr-traineddata-english xvfb-run gzip tar >/dev/null || exit 1
      PY=python3.11
    else
      zypper -n -q install python3 python3-tk tesseract-ocr \
        tesseract-ocr-traineddata-english xvfb-run gzip tar >/dev/null || exit 1
    fi
    for t in grim spectacle gnome-screenshot; do
      zypper -n -q info "$t" 2>/dev/null | grep -q "^Name" && WAYLAND_TOOLS="$WAYLAND_TOOLS $t"
    done ;;
  pacman)     # Arch Linux, Manjaro, EndeavourOS, CachyOS
    pacman -Syu --noconfirm --needed python tk tesseract tesseract-data-eng \
      xorg-server-xvfb >/dev/null || exit 1
    for t in grim spectacle gnome-screenshot; do
      pacman -Si "$t" >/dev/null 2>&1 && WAYLAND_TOOLS="$WAYLAND_TOOLS $t"
    done ;;
  xbps)       # Void Linux (glibc)
    xbps-install -Syu xbps >/dev/null 2>&1
    xbps-install -Syu >/dev/null 2>&1
    xbps-install -y python3 python3-tkinter tesseract-ocr xorg-server-xvfb >/dev/null || exit 1
    for t in grim spectacle gnome-screenshot; do
      xbps-query -R "$t" >/dev/null 2>&1 && WAYLAND_TOOLS="$WAYLAND_TOOLS $t"
    done ;;
  apk)        # Alpine Linux (musl: from source only)
    apk add -q python3 python3-tkinter tesseract-ocr tesseract-ocr-data-eng xvfb \
      font-dejavu >/dev/null || exit 1
    for t in grim spectacle gnome-screenshot; do
      apk search -q -x "$t" | grep -q . && WAYLAND_TOOLS="$WAYLAND_TOOLS $t"
    done ;;
  *) echo "unknown family $FAMILY"; exit 2 ;;
esac
grep PRETTY_NAME /etc/os-release
T=$(command -v tesseract || command -v tesseract-ocr)
echo "python: $($PY --version 2>&1)  tesseract: $($T --version 2>&1 | head -1)"
ldd --version 2>&1 | head -1 || true

gui_check() {   # $@ = command; it must still be running after 15 s
  command -v Xvfb >/dev/null || { echo "GUI: not checked (no Xvfb in this distro's repos)"; return 0; }
  Xvfb :91 -screen 0 1280x800x24 >/dev/null 2>&1 &
  XP=$!
  sleep 2
  DISPLAY=:91 timeout 15 "$@" >/tmp/gui.log 2>&1
  rc=$?
  kill $XP 2>/dev/null
  # stopped by timeout = still running after 15 s (GNU timeout: 124, BusyBox: 143)
  if [ $rc -eq 124 ] || [ $rc -eq 143 ]; then echo "GUI: ran 15 s without errors"; return 0; fi
  echo "GUI: exited with $rc"; tail -15 /tmp/gui.log; return 1
}

FAIL=""
say "from source"
export XDG_DATA_HOME=/tmp/mfm-src
if $PY -m venv /tmp/venv && /tmp/venv/bin/pip install -q -r requirements.txt; then
  /tmp/venv/bin/python mfm.py selftest || FAIL="$FAIL source-selftest"
  gui_check /tmp/venv/bin/python mfm.py gui || FAIL="$FAIL source-gui"
else
  FAIL="$FAIL source-install"
fi

if [ -n "$APP" ]; then
  say "released app"
  export XDG_DATA_HOME=/tmp/mfm-app
  if "$APP" selftest; then
    gui_check "$APP" || FAIL="$FAIL app-gui"
  else
    FAIL="$FAIL app-selftest"
  fi
fi

say "result"
echo "wayland screenshot tools packaged:${WAYLAND_TOOLS:- none}"
if [ -n "$FAIL" ]; then echo "FAILED:$FAIL"; exit 1; fi
echo "OK"
