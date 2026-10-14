#!/usr/bin/env python3
"""Genera el par de claves Ed25519 para firmar licencias.

Guarda la privada en keys/private.key (ignorada por git; RESPÁLDALA fuera del repo)
y escribe la pública en src/control_maletas/license_keys.py.
Si ya existe una clave privada no la sobrescribe (usa --force).
"""
import argparse
import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
PRIV = ROOT / "keys" / "private.key"
PUB_PY = ROOT / "src" / "control_maletas" / "license_keys.py"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if PRIV.exists() and not args.force:
        raise SystemExit(f"Ya existe {PRIV}. Use --force para reemplazarla (invalida licencias previas).")
    key = Ed25519PrivateKey.generate()
    raw_priv = key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    raw_pub = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    PRIV.parent.mkdir(exist_ok=True)
    PRIV.write_text(base64.b64encode(raw_priv).decode())
    PRIV.chmod(0o600)
    PUB_PY.write_text(
        '"""Clave PÚBLICA Ed25519 (raw, base64) con la que se verifican las licencias.\n\n'
        "La privada vive en keys/private.key (fuera de git). Ver tools/gen_keys.py.\n"
        '"""\n'
        f'PUBLIC_KEY_B64 = "{base64.b64encode(raw_pub).decode()}"\n'
    )
    print(f"Privada: {PRIV}\nPública escrita en: {PUB_PY}")


if __name__ == "__main__":
    main()
