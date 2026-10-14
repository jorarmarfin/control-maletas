#!/usr/bin/env bash
# Compila la app con PyInstaller (Linux o Windows/Git Bash).
# En Windows además genera Setup.exe (Inno Setup) y .msix si las herramientas existen.
#   ./build.sh            -> dist/ControlMaletas[/.exe]
#   ./build.sh --no-test  -> omite pytest
set -euo pipefail
cd "$(dirname "$0")"

RUN_TESTS=1
for a in "$@"; do [ "$a" = "--no-test" ] && RUN_TESTS=0; done

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) OS=windows; SEP=";" ;;
  *)                    OS=linux;   SEP=":" ;;
esac

if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"
else
  PYBIN="$(command -v python3 || command -v python)"
  "$PYBIN" -m venv .venv
  if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY=".venv/Scripts/python.exe"; fi
fi

echo ">> Dependencias de compilación"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements-dev.txt

if [ "$RUN_TESTS" = 1 ]; then
  echo ">> Tests"
  "$PY" -m pytest -q
fi

VERSION="$("$PY" -c "import sys; sys.path.insert(0,'src'); from control_maletas import __version__; print(__version__)")"
echo ">> Compilando ControlMaletas $VERSION ($OS)"
rm -rf build dist

"$PY" -m PyInstaller --noconfirm --clean --windowed \
  --name ControlMaletas \
  --icon assets/icon.ico \
  --paths src \
  --add-data "assets${SEP}assets" \
  --collect-data customtkinter --hidden-import PIL._tkinter_finder \
  --onedir \
  launcher.py

echo ">> Listo: dist/ControlMaletas/"

if [ "$OS" = windows ]; then
  # Ejecutable único portable (.exe)
  "$PY" -m PyInstaller --noconfirm --clean --windowed --onefile \
    --name ControlMaletas-portable --icon assets/icon.ico --paths src \
    --add-data "assets${SEP}assets" --collect-data customtkinter --hidden-import PIL._tkinter_finder \
    --distpath dist launcher.py
  echo ">> Portable: dist/ControlMaletas-portable.exe"

  # Instalador Inno Setup
  ISCC="$(command -v iscc || command -v ISCC.exe || true)"
  for p in "/c/Program Files (x86)/Inno Setup 6/ISCC.exe" "/c/Program Files/Inno Setup 6/ISCC.exe"; do
    [ -z "$ISCC" ] && [ -f "$p" ] && ISCC="$p"
  done
  if [ -n "$ISCC" ]; then
    echo ">> Inno Setup"
    "$ISCC" "//DAppVersion=$VERSION" packaging/inno/setup.iss
  else
    echo "!! Inno Setup no encontrado: se omite Setup.exe (https://jrsoftware.org/isdl.php)"
  fi

  # MSIX
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging/msix/build_msix.ps1 -Version "$VERSION" \
      || echo "!! MSIX no generado (¿falta Windows SDK / makeappx?)"
  fi
  ls -la dist installer 2>/dev/null || true
fi
