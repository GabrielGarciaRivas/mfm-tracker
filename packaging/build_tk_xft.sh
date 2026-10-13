#!/usr/bin/env bash
# python-build-standalone Pythons (uv, rye, pyenv's portable builds) ship Tk built
# without Xft, so Tk only sees a few old X11 bitmap fonts and can't use the bundled
# Inter font. This rebuilds the same Tk version with Xft (plus libXft itself) and
# makes a patched copy of that Python in build/python-xft.
# Usage: packaging/build_tk_xft.sh /path/to/portable/python3.x
# Needs git, a C compiler, make, and X11/Xrender/fontconfig/freetype headers.
set -euo pipefail
cd "$(dirname "$0")/.."
SRC_PY="$(cd "$(dirname "$1")/.." && pwd)"
W="$PWD/build/tk-xft"; mkdir -p "$W"
TKVER="$("$1" -c 'import tkinter as t; r=t.Tcl(); print(r.call("info","patchlevel"))')"
TAG="core-${TKVER//./-}"
[ -d "$W/xenocara" ] || { git clone -q --depth 1 --filter=blob:none --sparse https://github.com/openbsd/xenocara "$W/xenocara"; git -C "$W/xenocara" sparse-checkout set lib/libXft; }
[ -d "$W/tcl" ] || git clone -q --depth 1 --branch "$TAG" https://github.com/tcltk/tcl "$W/tcl"
[ -d "$W/tk" ] || git clone -q --depth 1 --branch "$TAG" https://github.com/tcltk/tk "$W/tk"
P="$W/prefix"
rm -rf "$W/xft-b" && cp -r "$W/xenocara/lib/libXft" "$W/xft-b" && chmod +x "$W/xft-b/configure" "$W/xft-b"/config.* "$W/xft-b"/install-sh
(cd "$W/xft-b" && ./configure --prefix="$P" --disable-static -q && make -s -j"$(nproc)" && make -s install) >/dev/null
mkdir -p "$W/tcl-b" "$W/tk-b"
(cd "$W/tcl-b" && "$W/tcl/unix/configure" --prefix="$P" --enable-shared -q && make -s -j"$(nproc)" && make -s install) >/dev/null
(cd "$W/tk-b" && PKG_CONFIG_PATH="$P/lib/pkgconfig" CFLAGS="-O2 -I$P/include" \
   "$W/tk/unix/configure" --prefix="$P" --with-tcl="$P/lib" --enable-shared --enable-xft -q && \
 make -s -j"$(nproc)" LDFLAGS="-L$P/lib -Wl,-rpath,'\$\$ORIGIN'") >/dev/null
OUT="$PWD/build/python-xft"
rm -rf "$OUT" && cp -a "$SRC_PY" "$OUT"
TKLIB="$(ls "$W/tk-b"/libtcl*tk*.so | head -1)"
cp "$TKLIB" "$OUT/lib/"
cp -L "$P/lib/libXft.so.2" "$OUT/lib/"
echo "Patched Python: $OUT/bin/$(basename "$1")"
