#!/bin/bash
# Builds "Free Market Tracker.app" on this Mac. Double-click it in Finder (the first
# time: right-click > Open). Afterwards the app in the "dist" folder works on its
# own: drag it to Applications, no Python or Homebrew needed to run it.
cd "$(dirname "$0")" || exit 1
chmod +x build_macos.sh 2>/dev/null

pause() { echo; read -r -p "Press Return to close this window." _; }

# Homebrew (for Tesseract OCR and, if needed, Python)
BREW="$(command -v brew || ls /opt/homebrew/bin/brew /usr/local/bin/brew 2>/dev/null | head -1)"
if [ -z "$BREW" ]; then
  echo "Installing Homebrew for the build (it will ask for your Mac password)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || { pause; exit 1; }
  BREW="$(ls /opt/homebrew/bin/brew /usr/local/bin/brew 2>/dev/null | head -1)"
fi
[ -n "$BREW" ] || { echo "Homebrew didn't install."; pause; exit 1; }
eval "$("$BREW" shellenv)"

if ! command -v tesseract >/dev/null 2>&1; then
  echo "Installing Tesseract OCR for the build..."
  brew install tesseract || { pause; exit 1; }
fi

# A Python with a modern Tk: python.org's, or Homebrew's with python-tk
have_python() {
  for c in $(ls /Library/Frameworks/Python.framework/Versions/3.*/bin/python3 2>/dev/null) \
           "$(brew --prefix)"/bin/python3.1[0-9] "$(brew --prefix)"/bin/python3; do
    [ -x "$c" ] && "$c" -c 'import sys, tkinter; assert sys.version_info >= (3, 10); assert tkinter.TkVersion >= 8.6' 2>/dev/null && return 0
  done
  return 1
}
if ! have_python; then
  echo "Installing Python 3.12 with Tk for the build..."
  brew install python@3.12 python-tk@3.12 || { pause; exit 1; }
fi

if ./build_macos.sh; then
  open ../dist
  echo
  echo "Built. Drag \"Free Market Tracker\" from the dist folder into Applications."
  echo "The first time you press Start monitoring, macOS asks for Screen Recording"
  echo "permission: allow it, then quit and reopen the app."
else
  echo
  echo "Build failed. The messages above say why."
fi
pause
