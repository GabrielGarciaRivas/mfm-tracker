#!/usr/bin/env bash
# Build the single-file Linux app "Free Market Tracker" (Python, Tk, Pillow and
# Tesseract OCR all inside). Needs, on the build machine only:
#   python 3.10+ with tkinter, tesseract + English data, and
#   pip install pyinstaller pillow pytesseract mss pyspellchecker certifi
# The Python's Tk must be built with Xft (distro Pythons are) or the app can't use
# the bundled Inter font; for a portable python-build-standalone Python, run
# packaging/build_tk_xft.sh first and use the Python it prints.
# Usage:  packaging/build_linux.sh            (uses python3)
#         PYTHON=/path/to/python packaging/build_linux.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
NAME="Free Market Tracker"
WORK="$PWD/build/linux"
rm -rf "$WORK" "dist/$NAME"
mkdir -p "$WORK/tesseract/lib" "$WORK/tesseract/tessdata"

# --- Tesseract: the binary, every library it needs except glibc itself, eng data.
# Best: a static build (packaging/build_tesseract_static.sh -> build/tesseract-static),
# which needs nothing but glibc and keeps the app small; else the system's tesseract.
TESS="${TESSERACT_BIN:-}"
[ -z "$TESS" ] && [ -x build/tesseract-static ] && TESS="$PWD/build/tesseract-static"
[ -z "$TESS" ] && { TESS="$(command -v tesseract)" || { echo "tesseract not found"; exit 1; }; }
echo "Bundling tesseract: $TESS"
cp -L "$TESS" "$WORK/tesseract/tesseract.bin"
{ ldd "$TESS" 2>/dev/null || true; } | awk '/=> \//{print $3}' | while read -r lib; do
  case "$(basename "$lib")" in
    libc.so*|libm.so*|libdl.so*|libpthread.so*|librt.so*|libresolv.so*|ld-linux*|libgcc_s.so*) ;;
    *) cp -L "$lib" "$WORK/tesseract/lib/" ;;
  esac
done
DATA=""
for d in /usr/share/tessdata /usr/share/tesseract-ocr/*/tessdata /usr/local/share/tessdata; do
  [ -f "$d/eng.traineddata" ] && DATA="$d" && break
done
[ -n "$DATA" ] || { echo "eng.traineddata not found"; exit 1; }
cp "$DATA/eng.traineddata" "$WORK/tesseract/tessdata/"
[ -d "$DATA/configs" ] && cp -r "$DATA/configs" "$WORK/tesseract/tessdata/"
cat > "$WORK/tesseract/tesseract-run" <<'SH'
#!/bin/sh
d="${0%/*}"
LD_LIBRARY_PATH="$d/lib" TESSDATA_PREFIX="$d/tessdata" exec "$d/tesseract.bin" "$@"
SH
chmod 755 "$WORK/tesseract/tesseract-run" "$WORK/tesseract/tesseract.bin"
"$WORK/tesseract/tesseract-run" --version | head -1

# --- the app
# portable Pythons keep libtcl/libtk next to libpython: let PyInstaller find them
# (sys.base_prefix/lib: a copied portable Python still reports its original LIBDIR)
PYLIB="$("$PY" -c 'import sys; print(sys.base_prefix + "/lib")')"
EXTRA=()
# a Tk patched by build_tk_xft.sh carries its own libXft next to it: ship that too
[ -f "$PYLIB/libXft.so.2" ] && EXTRA+=(--add-binary "$PYLIB/libXft.so.2:.")
LD_LIBRARY_PATH="$PYLIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
"$PY" -m PyInstaller --noconfirm --clean --onefile --windowed \
  --name "$NAME" \
  --icon "$PWD/packaging/icon.png" \
  --paths "$PWD" \
  --hidden-import mfm --hidden-import mfm_gui --hidden-import PIL._tkinter_finder --hidden-import PIL.ImageTk \
  --collect-data spellchecker --collect-data certifi --hidden-import certifi \
  --exclude-module pynput --strip \
  --exclude-module PIL._avif --exclude-module PIL.AvifImagePlugin \
  --exclude-module PIL._webp --exclude-module PIL.WebPImagePlugin \
  --exclude-module PIL._imagingcms --exclude-module PIL.ImageCms \
  --exclude-module PIL._imagingft \
  --add-data "$WORK/tesseract:tesseract" \
  --add-data "$PWD/packaging/icon.png:." \
  --add-data "$PWD/packaging/fonts:fonts" \
  "${EXTRA[@]}" \
  --workpath "$WORK/pyi" --specpath "$WORK" --distpath "$PWD/dist" \
  "$PWD/packaging/launcher.py"
chmod 755 "dist/$NAME"

# desktop entry, so it can also be added to the app menu
cat > "dist/free-market-tracker.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$NAME
Comment=MapleStory Classic Free Market price tracker
Exec="\$HOME/Applications/$NAME"
Icon=free-market-tracker
Terminal=false
Categories=Game;Utility;
EOF
cp packaging/icon.png dist/free-market-tracker.png
ls -la dist
