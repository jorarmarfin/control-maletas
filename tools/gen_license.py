#!/usr/bin/env python3
"""Emite un archivo de licencia (.lic) firmado.

Ejemplos:
  python tools/gen_license.py --type event --event "Retiro Octubre 2026" \\
      --licensee "Parroquia San José" --from 2026-10-01 --to 2026-10-31 --max-people 500
  python tools/gen_license.py --type master --licensee "Propietario"

La clave privada se toma de --key, de $CM_LICENSE_PRIVATE_KEY o de keys/private.key.
"""
import argparse
import base64
import os
import sys
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from control_maletas.licensing import sign_license  # noqa: E402


def load_private(path: str | None) -> Ed25519PrivateKey:
    env = os.environ.get("CM_LICENSE_PRIVATE_KEY")
    if path:
        raw = Path(path).read_text().strip()
    elif env:
        raw = env.strip()
    else:
        raw = (ROOT / "keys" / "private.key").read_text().strip()
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--type", choices=["event", "master"], required=True)
    ap.add_argument("--event", help="nombre exacto del evento (tipo event)")
    ap.add_argument("--licensee", default="")
    ap.add_argument("--from", dest="starts_at", help="YYYY-MM-DD")
    ap.add_argument("--to", dest="ends_at", help="YYYY-MM-DD")
    ap.add_argument("--max-people", type=int)
    ap.add_argument("--key")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.type == "event" and not a.event:
        ap.error("--event es obligatorio para licencias de evento")
    for d in (a.starts_at, a.ends_at):
        if d:
            date.fromisoformat(d)
    payload = {
        "id": uuid.uuid4().hex[:12],
        "type": a.type,
        "event": a.event if a.type == "event" else None,
        "licensee": a.licensee,
        "starts_at": a.starts_at,
        "ends_at": a.ends_at,
        "max_people": a.max_people,
        "issued_at": date.today().isoformat(),
    }
    text = sign_license(payload, load_private(a.key))
    out_dir = ROOT / "licenses_out"
    out_dir.mkdir(exist_ok=True)
    out = Path(a.out) if a.out else out_dir / f"{a.type}-{payload['id']}.lic"
    out.write_text(text, encoding="utf-8")
    print(f"Licencia escrita en {out}")


if __name__ == "__main__":
    main()
