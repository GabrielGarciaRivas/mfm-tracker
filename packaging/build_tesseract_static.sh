#!/usr/bin/env bash
# Build a self-contained Tesseract 5.3.4 (the version the OCR clean-up is tuned
# against) that needs nothing but glibc: Leptonica with PNG + zlib only, no
# curl/libarchive/ICU/OpenMP, static libstdc++. Output: build/tesseract-static.
# Needs git, cmake, ninja, a C/C++ compiler and static libpng + zlib
# (Arch: base-devel cmake ninja libpng zlib).
set -euo pipefail
cd "$(dirname "$0")/.."
W="$PWD/build/tess-src"; P="$W/prefix"
mkdir -p "$W"
[ -d "$W/leptonica" ] || git clone --depth 1 --branch 1.87.0 https://github.com/DanBloomberg/leptonica "$W/leptonica"
[ -d "$W/tesseract" ] || git clone --depth 1 --branch 5.3.4 https://github.com/tesseract-ocr/tesseract "$W/tesseract"
PNG_A="$(ls /usr/lib/x86_64-linux-gnu/libpng16.a /usr/lib/libpng16.a 2>/dev/null | head -1)"
Z_A="$(ls /usr/lib/x86_64-linux-gnu/libz.a /usr/lib/libz.a 2>/dev/null | head -1)"
cmake -S "$W/leptonica" -B "$W/lept-build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$P" \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_PROG=OFF -DSW_BUILD=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DENABLE_PNG=ON -DENABLE_ZLIB=ON -DENABLE_JPEG=OFF -DENABLE_TIFF=OFF -DENABLE_GIF=OFF -DENABLE_WEBP=OFF -DENABLE_OPENJPEG=OFF \
  -DCMAKE_DISABLE_FIND_PACKAGE_JPEG=ON -DCMAKE_DISABLE_FIND_PACKAGE_TIFF=ON -DCMAKE_DISABLE_FIND_PACKAGE_GIF=ON \
  -DCMAKE_DISABLE_FIND_PACKAGE_WebP=ON -DCMAKE_DISABLE_FIND_PACKAGE_OpenJPEG=ON \
  ${PNG_A:+-DPNG_LIBRARY="$PNG_A"} ${Z_A:+-DZLIB_LIBRARY="$Z_A"}
ninja -C "$W/lept-build" install
cmake -S "$W/tesseract" -B "$W/tess-build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$P" \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_TRAINING_TOOLS=OFF -DBUILD_TESTS=OFF -DDISABLE_CURL=ON -DDISABLE_ARCHIVE=ON \
  -DDISABLE_TIFF=ON -DOPENMP_BUILD=OFF -DGRAPHICS_DISABLED=ON -DENABLE_NATIVE=OFF -DSW_BUILD=OFF \
  -DLeptonica_DIR="$P/lib/cmake/leptonica" -DCMAKE_EXE_LINKER_FLAGS="-static-libstdc++ -static-libgcc"
ninja -C "$W/tess-build" tesseract
cp "$W/tess-build/bin/tesseract" build/tesseract-static
strip build/tesseract-static
ldd build/tesseract-static || true
echo "Built build/tesseract-static"
