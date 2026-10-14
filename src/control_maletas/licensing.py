"""Licencias offline firmadas con Ed25519.

Formato del archivo .lic (JSON):
    {"payload": {...}, "signature": "<base64>"}
La firma cubre el JSON canónico del payload (claves ordenadas, sin espacios).

Tipos:
  - event : válida solo para el evento con ese nombre.
  - master: sin límites, cualquier evento (licencia del propietario).
Sin licencia: modo demo (1 evento, 5 personas).
"""
from __future__ import annotations

import base64
import json
import sqlite3
from dataclasses import dataclass
from datetime import date

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from . import license_keys
from .errors import LicenseError

DEMO_MAX_EVENTS = 1
DEMO_MAX_PEOPLE = 5


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign_license(payload: dict, private_key: Ed25519PrivateKey) -> str:
    sig = private_key.sign(canonical(payload))
    return json.dumps(
        {"payload": payload, "signature": base64.b64encode(sig).decode()},
        ensure_ascii=False,
        indent=2,
    )


def load_public_key(b64: str | None = None) -> Ed25519PublicKey:
    raw = base64.b64decode(b64 or license_keys.PUBLIC_KEY_B64)
    return Ed25519PublicKey.from_public_bytes(raw)


@dataclass(frozen=True)
class LicenseInfo:
    id: str
    type: str  # 'event' | 'master'
    event: str | None
    licensee: str | None
    starts_at: str | None
    ends_at: str | None
    max_people: int | None

    def is_valid_on(self, today: date) -> bool:
        if self.starts_at and today < date.fromisoformat(self.starts_at):
            return False
        if self.ends_at and today > date.fromisoformat(self.ends_at):
            return False
        return True

    @classmethod
    def from_payload(cls, p: dict) -> "LicenseInfo":
        try:
            ltype = p["type"]
            if ltype not in ("event", "master"):
                raise ValueError("tipo desconocido")
            if ltype == "event" and not p.get("event"):
                raise ValueError("falta el nombre del evento")
            return cls(
                id=str(p["id"]),
                type=ltype,
                event=p.get("event"),
                licensee=p.get("licensee"),
                starts_at=p.get("starts_at"),
                ends_at=p.get("ends_at"),
                max_people=p.get("max_people"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise LicenseError(f"Licencia con formato inválido: {exc}") from exc


def verify_license_text(text: str, public_key: Ed25519PublicKey | None = None) -> LicenseInfo:
    try:
        doc = json.loads(text)
        payload = doc["payload"]
        sig = base64.b64decode(doc["signature"])
    except (ValueError, KeyError, TypeError) as exc:
        raise LicenseError("El archivo de licencia no es válido.") from exc
    try:
        (public_key or load_public_key()).verify(sig, canonical(payload))
    except InvalidSignature as exc:
        raise LicenseError("La firma de la licencia no es válida (archivo alterado).") from exc
    except ValueError as exc:
        raise LicenseError("La clave pública de la aplicación no está configurada.") from exc
    return LicenseInfo.from_payload(payload)


def _norm(s: str | None) -> str:
    return (s or "").strip().casefold()


@dataclass(frozen=True)
class Limits:
    max_people: int | None  # None = sin límite
    label: str
    licensed: bool


class LicenseManager:
    def __init__(self, conn: sqlite3.Connection, public_key: Ed25519PublicKey | None = None):
        self.conn = conn
        self._public_key = public_key

    # --- instalación -------------------------------------------------
    def install(self, text: str) -> LicenseInfo:
        info = verify_license_text(text, self._public_key)
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO licenses
                   (id,type,event_name,starts_at,ends_at,max_people,raw_file)
                   VALUES (?,?,?,?,?,?,?)""",
                (info.id, info.type, info.event, info.starts_at, info.ends_at,
                 info.max_people, text),
            )
        return info

    def installed(self) -> list[LicenseInfo]:
        out = []
        for row in self.conn.execute("SELECT raw_file FROM licenses ORDER BY activated_at"):
            try:
                out.append(verify_license_text(row["raw_file"], self._public_key))
            except LicenseError:
                continue
        return out

    def remove(self, license_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM licenses WHERE id=?", (license_id,))

    # --- consultas ---------------------------------------------------
    def _valid(self, today: date) -> list[LicenseInfo]:
        return [l for l in self.installed() if l.is_valid_on(today)]

    def master(self, today: date | None = None) -> LicenseInfo | None:
        today = today or date.today()
        return next((l for l in self._valid(today) if l.type == "master"), None)

    def event_license(self, event_name: str, today: date | None = None) -> LicenseInfo | None:
        today = today or date.today()
        return next(
            (l for l in self._valid(today)
             if l.type == "event" and _norm(l.event) == _norm(event_name)),
            None,
        )

    def limits_for_event(self, event_name: str, today: date | None = None) -> Limits:
        if self.master(today):
            return Limits(None, "Licencia maestra", True)
        lic = self.event_license(event_name, today)
        if lic:
            return Limits(lic.max_people, f"Licencia del evento ({lic.licensee or 'sin titular'})", True)
        return Limits(DEMO_MAX_PEOPLE, f"Modo demo (máx. {DEMO_MAX_PEOPLE} personas)", False)

    def can_create_event(self, new_name: str, events_created: int, today: date | None = None) -> bool:
        if events_created < DEMO_MAX_EVENTS:
            return True
        if self.master(today):
            return True
        return self.event_license(new_name, today) is not None
