"""Huella estable del equipo para atar licencias (opcional).

Formato: 16 caracteres base32 (A-Z, 2-7) en 4 grupos: XXXX-XXXX-XXXX-XXXX.
Se deriva con SHA-256 de un identificador del sistema; no se puede invertir.
"""
from __future__ import annotations

import base64
import hashlib
import subprocess
import sys
import uuid
from pathlib import Path

_SALT = "control-maletas|machine|v1|"


def _raw_machine_id() -> str:
    try:
        if sys.platform.startswith("win"):
            import winreg  # type: ignore[import-not-found]

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            ) as k:
                return str(winreg.QueryValueEx(k, "MachineGuid")[0])
        if sys.platform == "darwin":
            out = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], text=True, timeout=5)
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    return line.split('"')[-2]
        for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            f = Path(p)
            if f.exists() and f.read_text().strip():
                return f.read_text().strip()
    except Exception:
        pass
    return f"mac-{uuid.getnode():012x}"  # último recurso


def format_fingerprint(raw_digest: bytes) -> str:
    b32 = base64.b32encode(raw_digest[:10]).decode()  # 80 bits -> 16 caracteres
    return "-".join(b32[i:i + 4] for i in range(0, 16, 4))


def machine_fingerprint() -> str:
    digest = hashlib.sha256((_SALT + _raw_machine_id()).encode()).digest()
    return format_fingerprint(digest)


def normalize_fingerprint(text: str | None) -> str:
    return "".join((text or "").replace("-", "").split()).upper()
