"""Lógica de negocio sobre SQLite: eventos, zonas, registro, búsqueda y retiro."""
from __future__ import annotations

import csv
import re
import secrets
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .errors import LimitError, NoCapacityError, ValidationError
from .licensing import DEMO_MAX_EVENTS, LicenseManager

# Alfabeto sin caracteres ambiguos (0/O, 1/I/L)
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
TICKET_LEN = 6
DNI_RE = re.compile(r"^\d{8}$")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.casefold().split())


def clean_ticket_code(raw: str) -> str:
    """Acepta el contenido del QR ('CM:ABC123') o el código escrito a mano."""
    code = (raw or "").strip().upper()
    if code.startswith("CM:"):
        code = code[3:]
    return code.replace("-", "").replace(" ", "")


@dataclass
class Bulto:
    id: int
    description: str
    location: str | None
    status: str
    stored_at: str
    delivered_at: str | None


@dataclass
class PersonRecord:
    id: int
    event_id: int
    full_name: str
    dni: str
    phone: str
    notes: str
    ticket_code: str
    created_at: str
    bultos: list[Bulto] = field(default_factory=list)

    @property
    def stored(self) -> list[Bulto]:
        return [b for b in self.bultos if b.status == "stored"]


@dataclass
class ZoneStatus:
    id: int
    code: str
    name: str
    capacity: int
    occupied: int

    @property
    def free(self) -> int:
        return self.capacity - self.occupied


class Store:
    def __init__(self, conn: sqlite3.Connection, licenses: LicenseManager | None = None):
        self.conn = conn
        self.licenses = licenses or LicenseManager(conn)

    # ------------------------------------------------------------ meta
    def _meta_int(self, key: str) -> int:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return int(row["value"]) if row else 0

    def _meta_set(self, key: str, value: int) -> None:
        self.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, str(value)))

    # ---------------------------------------------------------- eventos
    def events_created_count(self) -> int:
        real = self.conn.execute("SELECT COUNT(*) c FROM events").fetchone()["c"]
        return max(real, self._meta_int("events_created"))

    def create_event(self, name: str, starts_at: str | None = None, ends_at: str | None = None,
                     default_zone_capacity: int = 50) -> int:
        name = (name or "").strip()
        if not name:
            raise ValidationError("El nombre del evento es obligatorio.")
        starts_at, ends_at = starts_at or None, ends_at or None
        try:
            d1 = date.fromisoformat(starts_at) if starts_at else None
            d2 = date.fromisoformat(ends_at) if ends_at else None
        except ValueError:
            raise ValidationError("Las fechas deben tener formato AAAA-MM-DD.") from None
        if d1 and d2 and d2 < d1:
            raise ValidationError("La fecha de fin no puede ser anterior al inicio.")
        if not self.licenses.can_create_event(name, self.events_created_count()):
            raise LimitError(
                f"El modo demo permite solo {DEMO_MAX_EVENTS} evento. "
                "Active una licencia para crear más eventos."
            )
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO events(name,starts_at,ends_at,active) VALUES(?,?,?,0)",
                (name, starts_at or None, ends_at or None),
            )
            event_id = cur.lastrowid
            self._meta_set("events_created", self.events_created_count() + 1)
        self.add_zone(event_id, "A", "Principal", default_zone_capacity)
        if self.active_event() is None:
            self.set_active_event(event_id)
        return event_id

    def list_events(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM events ORDER BY id DESC").fetchall()

    def active_event(self) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM events WHERE active=1").fetchone()

    def set_active_event(self, event_id: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE events SET active=0")
            self.conn.execute("UPDATE events SET active=1 WHERE id=?", (event_id,))

    # ------------------------------------------------------------ zonas
    def add_zone(self, event_id: int, code: str, name: str, capacity: int) -> int:
        code = (code or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{1,4}", code):
            raise ValidationError("El código de zona debe tener 1 a 4 letras o números.")
        if capacity < 1 or capacity > 999:
            raise ValidationError("La capacidad debe estar entre 1 y 999.")
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO zones(event_id,code,name,capacity) VALUES(?,?,?,?)",
                    (event_id, code, (name or code).strip(), capacity),
                )
                zone_id = cur.lastrowid
                self.conn.executemany(
                    "INSERT INTO locations(zone_id,label) VALUES(?,?)",
                    [(zone_id, f"{code}-{i:02d}") for i in range(1, capacity + 1)],
                )
        except sqlite3.IntegrityError as exc:
            raise ValidationError(f"Ya existe la zona {code} en este evento.") from exc
        return zone_id

    def zone_statuses(self, event_id: int) -> list[ZoneStatus]:
        rows = self.conn.execute(
            """SELECT z.id, z.code, z.name, z.capacity,
                      COALESCE(SUM(l.occupied),0) AS occupied
               FROM zones z LEFT JOIN locations l ON l.zone_id=z.id
               WHERE z.event_id=? GROUP BY z.id ORDER BY z.code""",
            (event_id,),
        ).fetchall()
        return [ZoneStatus(r["id"], r["code"], r["name"], r["capacity"], r["occupied"]) for r in rows]

    def zone_locations(self, zone_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT l.id, l.label, l.occupied, p.full_name
               FROM locations l
               LEFT JOIN luggage g ON g.location_id=l.id AND g.status='stored'
               LEFT JOIN people p ON p.id=g.person_id
               WHERE l.zone_id=? ORDER BY l.id""",
            (zone_id,),
        ).fetchall()

    def _free_locations(self, event_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT l.id, l.label, z.code FROM locations l
               JOIN zones z ON z.id=l.zone_id
               WHERE z.event_id=? AND l.occupied=0 ORDER BY z.code, l.id""",
            (event_id,),
        ).fetchall()

    @staticmethod
    def _pick_locations(free: list[sqlite3.Row], n: int) -> list[sqlite3.Row]:
        """Prefiere una sola zona con espacio para todos; si no, rellena en orden."""
        by_zone: dict[str, list[sqlite3.Row]] = {}
        for row in free:
            by_zone.setdefault(row["code"], []).append(row)
        for rows in by_zone.values():
            if len(rows) >= n:
                return rows[:n]
        return free[:n]

    # --------------------------------------------------------- registro
    def people_count(self, event_id: int) -> int:
        real = self.conn.execute(
            "SELECT COUNT(*) c FROM people WHERE event_id=?", (event_id,)
        ).fetchone()["c"]
        return real

    def _new_ticket_code(self, event_id: int) -> str:
        for _ in range(50):
            code = "".join(secrets.choice(_ALPHABET) for _ in range(TICKET_LEN))
            exists = self.conn.execute(
                "SELECT 1 FROM people WHERE event_id=? AND ticket_code=?", (event_id, code)
            ).fetchone()
            if not exists:
                return code
        raise RuntimeError("No se pudo generar un código único")

    def find_by_dni(self, event_id: int, dni: str) -> PersonRecord | None:
        row = self.conn.execute(
            "SELECT * FROM people WHERE event_id=? AND dni=?", (event_id, dni.strip())
        ).fetchone()
        return self._hydrate(row) if row else None

    def register(self, event_id: int, full_name: str, dni: str, bultos: list[str],
                 phone: str = "", notes: str = "") -> PersonRecord:
        full_name = " ".join((full_name or "").split())
        dni = (dni or "").strip()
        if len(full_name) < 3:
            raise ValidationError("Ingrese el nombre completo.")
        if not DNI_RE.match(dni):
            raise ValidationError("El DNI debe tener 8 dígitos.")
        if not bultos:
            raise ValidationError("Agregue al menos un bulto.")
        if self.find_by_dni(event_id, dni):
            raise ValidationError("Ese DNI ya está registrado en este evento.")

        event = self.conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        limits = self.licenses.limits_for_event(event["name"])
        if limits.max_people is not None:
            used = max(self.people_count(event_id), self._meta_int(f"people_{event_id}"))
            if used >= limits.max_people:
                if limits.licensed:
                    raise LimitError(
                        f"Su licencia permite registrar hasta {limits.max_people} personas en este "
                        "evento y ya se alcanzó ese máximo. Active una licencia con mayor capacidad.",
                        demo=False)
                raise LimitError(
                    f"La versión demo permite registrar hasta {limits.max_people} personas y ya "
                    "se alcanzó ese máximo. Active una licencia para continuar registrando.")
        picked = self._allocate(event_id, len(bultos))
        code = self._new_ticket_code(event_id)
        with self.conn:
            cur = self.conn.execute(
                """INSERT INTO people(event_id,full_name,full_name_norm,dni,phone,notes,ticket_code)
                   VALUES (?,?,?,?,?,?,?)""",
                (event_id, full_name, normalize(full_name), dni,
                 (phone or "").strip(), (notes or "").strip(), code),
            )
            person_id = cur.lastrowid
            self._insert_bultos(person_id, code, bultos, picked)
            self._meta_set(f"people_{event_id}", self.people_count(event_id))
        return self.get_person(person_id)

    def add_bultos(self, person_id: int, bultos: list[str]) -> PersonRecord:
        if not bultos:
            raise ValidationError("Agregue al menos un bulto.")
        person = self.get_person(person_id)
        picked = self._allocate(person.event_id, len(bultos))
        with self.conn:
            self._insert_bultos(person_id, person.ticket_code, bultos, picked)
        return self.get_person(person_id)

    def _allocate(self, event_id: int, n: int) -> list[sqlite3.Row]:
        free = self._free_locations(event_id)
        if len(free) < n:
            raise NoCapacityError(
                f"No hay ubicaciones libres suficientes (necesita {n}, hay {len(free)}). "
                "Agregue una zona o libere espacio."
            )
        return self._pick_locations(free, n)

    def _insert_bultos(self, person_id: int, code: str, bultos: list[str],
                       locations: list[sqlite3.Row]) -> None:
        for desc, loc in zip(bultos, locations):
            self.conn.execute(
                "INSERT INTO luggage(person_id,ticket_code,description,location_id) VALUES(?,?,?,?)",
                (person_id, code, (desc or "").strip(), loc["id"]),
            )
            self.conn.execute("UPDATE locations SET occupied=1 WHERE id=?", (loc["id"],))

    # --------------------------------------------------------- consulta
    def _hydrate(self, row: sqlite3.Row) -> PersonRecord:
        bultos = self.conn.execute(
            """SELECT g.id, g.description, l.label, g.status, g.stored_at, g.delivered_at
               FROM luggage g LEFT JOIN locations l ON l.id=g.location_id
               WHERE g.person_id=? ORDER BY g.id""",
            (row["id"],),
        ).fetchall()
        return PersonRecord(
            id=row["id"], event_id=row["event_id"], full_name=row["full_name"],
            dni=row["dni"], phone=row["phone"] or "", notes=row["notes"] or "",
            ticket_code=row["ticket_code"], created_at=row["created_at"],
            bultos=[Bulto(b["id"], b["description"] or "", b["label"], b["status"],
                          b["stored_at"], b["delivered_at"]) for b in bultos],
        )

    def get_person(self, person_id: int) -> PersonRecord:
        row = self.conn.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone()
        return self._hydrate(row)

    def search(self, event_id: int, query: str, limit: int = 50) -> list[PersonRecord]:
        q = (query or "").strip()
        if not q:
            rows = self.conn.execute(
                "SELECT * FROM people WHERE event_id=? ORDER BY id DESC LIMIT ?", (event_id, limit)
            ).fetchall()
            return [self._hydrate(r) for r in rows]
        code = clean_ticket_code(q)
        like_name = "%" + "%".join(normalize(q).split()) + "%"
        rows = self.conn.execute(
            """SELECT * FROM people WHERE event_id=? AND
                  (full_name_norm LIKE ? OR dni LIKE ? OR ticket_code=?)
               ORDER BY full_name_norm LIMIT ?""",
            (event_id, like_name, q + "%", code, limit),
        ).fetchall()
        return [self._hydrate(r) for r in rows]

    def find_by_ticket(self, event_id: int, raw_code: str) -> PersonRecord | None:
        row = self.conn.execute(
            "SELECT * FROM people WHERE event_id=? AND ticket_code=?",
            (event_id, clean_ticket_code(raw_code)),
        ).fetchone()
        return self._hydrate(row) if row else None

    # ----------------------------------------------------------- retiro
    def deliver(self, person_id: int, luggage_ids: list[int] | None = None) -> int:
        """Marca bultos como entregados y libera sus ubicaciones. Devuelve cuántos."""
        rows = self.conn.execute(
            "SELECT id, location_id FROM luggage WHERE person_id=? AND status='stored'",
            (person_id,),
        ).fetchall()
        if luggage_ids is not None:
            wanted = set(luggage_ids)
            rows = [r for r in rows if r["id"] in wanted]
        with self.conn:
            for r in rows:
                self.conn.execute(
                    "UPDATE luggage SET status='delivered', delivered_at=datetime('now','localtime') WHERE id=?",
                    (r["id"],),
                )
                if r["location_id"]:
                    self.conn.execute("UPDATE locations SET occupied=0 WHERE id=?", (r["location_id"],))
        return len(rows)

    # ----------------------------------------------------- estadísticas
    def stats(self, event_id: int) -> dict:
        r = self.conn.execute(
            """SELECT COUNT(DISTINCT p.id) people,
                      COALESCE(SUM(g.status='stored'),0) stored,
                      COALESCE(SUM(g.status='delivered'),0) delivered
               FROM people p LEFT JOIN luggage g ON g.person_id=p.id
               WHERE p.event_id=?""",
            (event_id,),
        ).fetchone()
        return {"people": r["people"], "stored": r["stored"], "delivered": r["delivered"]}

    def dashboard_events(self) -> list[sqlite3.Row]:
        """Una fila por evento con personas y bultos en custodia / entregados."""
        return self.conn.execute(
            """SELECT e.id, e.name, e.active, e.starts_at, e.ends_at,
                      COUNT(DISTINCT p.id) AS people,
                      COALESCE(SUM(g.status='stored'),0) AS stored,
                      COALESCE(SUM(g.status='delivered'),0) AS delivered
               FROM events e
               LEFT JOIN people p ON p.event_id=e.id
               LEFT JOIN luggage g ON g.person_id=p.id
               GROUP BY e.id ORDER BY e.id DESC"""
        ).fetchall()

    def recent_people(self, event_id: int, limit: int = 5) -> list[PersonRecord]:
        rows = self.conn.execute(
            "SELECT * FROM people WHERE event_id=? ORDER BY id DESC LIMIT ?", (event_id, limit)
        ).fetchall()
        return [self._hydrate(r) for r in rows]

    def oldest_pending(self, event_id: int, limit: int = 5) -> list[tuple[PersonRecord, str]]:
        """Personas con equipaje aún en custodia, de la más antigua a la más reciente."""
        rows = self.conn.execute(
            """SELECT p.id, MIN(g.stored_at) AS since
               FROM people p JOIN luggage g ON g.person_id=p.id
               WHERE p.event_id=? AND g.status='stored'
               GROUP BY p.id ORDER BY since, p.id LIMIT ?""",
            (event_id, limit),
        ).fetchall()
        return [(self.get_person(r["id"]), r["since"]) for r in rows]

    def registrations_by_hour(self, event_id: int) -> list[int]:
        counts = [0] * 24
        for r in self.conn.execute(
            "SELECT CAST(strftime('%H', created_at) AS INTEGER) h, COUNT(*) c "
            "FROM people WHERE event_id=? GROUP BY h", (event_id,)
        ):
            counts[r["h"]] = r["c"]
        return counts

    def export_csv(self, event_id: int, path: str | Path) -> int:
        rows = self.conn.execute(
            """SELECT p.ticket_code, p.full_name, p.dni, p.phone, g.description,
                      l.label AS ubicacion, g.status, g.stored_at, g.delivered_at
               FROM people p JOIN luggage g ON g.person_id=p.id
               LEFT JOIN locations l ON l.id=g.location_id
               WHERE p.event_id=? ORDER BY p.id, g.id""",
            (event_id,),
        ).fetchall()
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["codigo", "nombre", "dni", "telefono", "bulto", "ubicacion",
                        "estado", "ingreso", "retiro"])
            for r in rows:
                w.writerow(list(r))
        return len(rows)
