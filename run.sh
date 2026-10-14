#!/usr/bin/env bash
# Ejecuta la app en desarrollo: crea .venv si falta e instala dependencias.
set -euo pipefail
cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then   # Git Bash en Windows
  PY=".venv/Scripts/python.exe"
else
  PYBIN="$(command -v python3 || command -v python || true)"
  [ -n "$PYBIN" ] || { echo "Python 3.10+ no encontrado"; exit 1; }
  echo ">> Creando entorno virtual .venv"
  "$PYBIN" -m venv .venv
  if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY=".venv/Scripts/python.exe"; fi
fi

# Reinstala solo si cambió requirements.txt
STAMP=".venv/.requirements.stamp"
if [ ! -f "$STAMP" ] || [ requirements.txt -nt "$STAMP" ]; then
  echo ">> Instalando dependencias"
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet -r requirements.txt
  touch "$STAMP"
fi

exec "$PY" launcher.py "$@"
