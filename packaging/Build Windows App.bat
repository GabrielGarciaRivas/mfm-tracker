@echo off
rem Builds "Free Market Tracker.exe" on this PC. Run once; afterwards the .exe in
rem the "dist" folder works on its own (copy it anywhere, no Python needed).
setlocal
cd /d "%~dp0"
where py >nul 2>nul || where python >nul 2>nul || (
  echo Installing Python for the build...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
)
if not exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" (
  echo Installing Tesseract OCR for the build...
  winget install -e --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
)
where py >nul 2>nul && (set PYTHON=py) || (set PYTHON=python)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 (
  echo.
  echo Build failed. If Python or Tesseract was just installed, close this window and run it again.
) else (
  explorer "%~dp0..\dist"
)
pause
