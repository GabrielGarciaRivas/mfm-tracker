#!/usr/bin/env bash
# Build "Free Market Tracker.app" for macOS (Python, Tk, Pillow and Tesseract OCR
# all inside; the Mac that runs it needs nothing installed). Needs, on the build
# Mac only:
#   - Homebrew's tesseract           (brew install tesseract)
#   - Python 3.10+ with Tk 8.6+      (python.org installer, or
#                                     brew install python@3.12 python-tk@3.12)
# "Build macOS App.command" next to this file installs both and runs this script.
# The app is built for this Mac's processor (Apple silicon or Intel).
# Usage:  packaging/build_macos.sh
#         PYTHON=/path/to/python3 TESSERACT=/path/to/tesseract packaging/build_macos.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
NAME="Free Market Tracker"
WORK="$ROOT/build/macos"
BREW="$(command -v brew || ls /opt/homebrew/bin/brew /usr/local/bin/brew 2>/dev/null | head -1 || true)"
BREW_PREFIX="$([ -n "$BREW" ] && "$BREW" --prefix || echo /opt/homebrew)"

# --- Python for building: one with a modern Tk (Apple's own python3 is too old)
good_python() {
  "$1" -c 'import sys, tkinter; assert sys.version_info >= (3, 10); assert tkinter.TkVersion >= 8.6' 2>/dev/null
}
PY=""
for c in ${PYTHON:-} \
         $(ls -r /Library/Frameworks/Python.framework/Versions/3.*/bin/python3 2>/dev/null) \
         "$BREW_PREFIX"/bin/python3.13 "$BREW_PREFIX"/bin/python3.12 "$BREW_PREFIX"/bin/python3.11 \
         "$BREW_PREFIX"/bin/python3 python3; do
  if command -v "$c" >/dev/null 2>&1 && good_python "$c"; then PY="$(command -v "$c")"; break; fi
done
if [ -z "$PY" ]; then
  echo "No Python 3.10+ with Tk found. Install one of:"
  echo "  brew install python@3.12 python-tk@3.12"
  echo "  or the macOS installer from https://www.python.org/downloads/"
  exit 1
fi
echo "Python: $PY ($("$PY" -c 'import sys, tkinter; print(sys.version.split()[0], "Tk", tkinter.TkVersion)'))"

rm -rf "$WORK" "dist/$NAME.app" "dist/$NAME"
mkdir -p "$WORK"
"$PY" -m venv "$WORK/venv"
VPY="$WORK/venv/bin/python"
"$VPY" -m pip install --upgrade pip
"$VPY" -m pip install pyinstaller pillow pytesseract mss pyspellchecker certifi

# --- Tesseract: the program, the Homebrew libraries it uses, English data only
TESS="${TESSERACT:-}"
[ -z "$TESS" ] && TESS="$(command -v tesseract || true)"
[ -z "$TESS" ] && [ -x "$BREW_PREFIX/bin/tesseract" ] && TESS="$BREW_PREFIX/bin/tesseract"
[ -n "$TESS" ] || { echo "tesseract not found. Install it: brew install tesseract"; exit 1; }
TESSDATA="$("$TESS" --list-langs 2>&1 | sed -n 's/.*languages in "\(.*\)".*/\1/p' | head -1)"
TESSDATA="${TESSDATA%/}"
[ -f "$TESSDATA/eng.traineddata" ] || TESSDATA="$BREW_PREFIX/share/tessdata"
[ -f "$TESSDATA/eng.traineddata" ] || { echo "eng.traineddata not found (looked in $TESSDATA)"; exit 1; }
echo "Bundling tesseract: $TESS (data: $TESSDATA)"
"$VPY" packaging/mac_bundle_tesseract.py "$TESS" "$WORK/tesseract" "$TESSDATA"
"$WORK/tesseract/tesseract-run" --version | head -1

# --- app icon (.icns) from icon.png
ICONSET="$WORK/icon.iconset"
mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z $s $s packaging/icon.png --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s * 2)) $((s * 2)) packaging/icon.png --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$WORK/icon.icns"

# --- the app
"$VPY" -m PyInstaller --noconfirm --clean --windowed \
  --name "$NAME" \
  --icon "$WORK/icon.icns" \
  --osx-bundle-identifier io.github.mfm-tracker.free-market-tracker \
  --paths "$ROOT" \
  --hidden-import mfm --hidden-import mfm_gui --hidden-import mfm_shared --hidden-import mfm_google_client \
  --hidden-import PIL._tkinter_finder --hidden-import PIL.ImageTk \
  --collect-data spellchecker --collect-data certifi --hidden-import certifi \
  --exclude-module pynput \
  --add-data "$WORK/tesseract:tesseract" \
  --add-data "$ROOT/packaging/icon.png:." \
  --add-data "$ROOT/packaging/fonts:fonts" \
  --workpath "$WORK/pyi" --specpath "$WORK" --distpath "$ROOT/dist" \
  "$ROOT/packaging/launcher.py"
rm -rf "dist/$NAME"          # the loose folder; the .app holds the same files

APP="dist/$NAME.app"
# the app shows a version in Finder's Get Info
VERSION="$("$VPY" -c 'import sys; sys.path.insert(0, "."); import mfm; print(mfm.VERSION)' 2>/dev/null || true)"
if [ -n "$VERSION" ]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$APP/Contents/Info.plist" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$APP/Contents/Info.plist"
  codesign --force --deep --sign - "$APP"
fi

# --- check that OCR works from inside the finished app
"$APP/Contents/MacOS/$NAME" selftest

# --- a zip that keeps the app intact (for copying to another Mac)
ditto -c -k --sequesterRsrc --keepParent "$APP" "dist/$NAME (macOS).zip"
echo
echo "Done: $ROOT/$APP"
echo "      $ROOT/dist/$NAME (macOS).zip"
