import time

import pytest

from control_maletas.errors import LimitError, NoCapacityError, ValidationError
from control_maletas.store import clean_ticket_code, normalize


def test_normalize_and_ticket_code():
    assert normalize("  José   PÉREZ ") == "jose perez"
    assert clean_ticket_code("cm:abc-123") == "ABC123"


def test_register_three_bultos(store, event_id):
    p = store.register(event_id, "José Pérez", "12345678", ["maleta roja", "mochila", ""])
    assert len(p.bultos) == 3
    assert len({b.location for b in p.bultos}) == 3
    assert len(p.ticket_code) == 6
    zone = store.zone_statuses(event_id)[0]
    assert zone.occupied == 3


def test_dni_validation_and_duplicate(store, event_id):
    with pytest.raises(ValidationError):
        store.register(event_id, "Ana Díaz", "123", ["x"])
    store.register(event_id, "Ana Díaz", "12345678", ["x"])
    assert store.find_by_dni(event_id, "12345678") is not None
    with pytest.raises(ValidationError):
        store.register(event_id, "Ana Díaz", "12345678", ["x"])


def test_add_bultos_to_existing(store, event_id):
    p = store.register(event_id, "Ana Díaz", "12345678", ["x"])
    p2 = store.add_bultos(p.id, ["y", "z"])
    assert len(p2.bultos) == 3
    assert {b for b in (bb.status for bb in p2.bultos)} == {"stored"}


def test_no_capacity(store, conn):
    ev = store.create_event("Mini", default_zone_capacity=2)
    store.register(ev, "Ana Díaz", "11111111", ["a", "b"])
    with pytest.raises(NoCapacityError):
        store.register(ev, "Luis Paz", "22222222", ["a"])
    assert store.people_count(ev) == 1  # no se registró


def test_prefers_single_zone(store, event_id):
    store.add_zone(event_id, "B", "Segunda", 5)
    store.register(event_id, "Uno Uno", "10000001", ["a"] * 8)  # llena casi A (10)
    p = store.register(event_id, "Dos Dos", "10000002", ["a"] * 3)  # A solo tiene 2 libres
    assert {b.location[0] for b in p.bultos} == {"B"}


def test_search_by_name_dni_code(store, event_id):
    p = store.register(event_id, "José Pérez Ríos", "12345678", ["m"])
    assert store.search(event_id, "perez")[0].id == p.id
    assert store.search(event_id, "jose rios")[0].id == p.id
    assert store.search(event_id, "1234")[0].id == p.id
    assert store.search(event_id, f"CM:{p.ticket_code}")[0].id == p.id
    assert store.search(event_id, "zzz") == []


def test_deliver_frees_location(store, event_id):
    p = store.register(event_id, "Ana Díaz", "12345678", ["a", "b"])
    assert store.deliver(p.id, [p.bultos[0].id]) == 1
    assert store.zone_statuses(event_id)[0].occupied == 1
    assert store.deliver(p.id) == 1
    assert store.zone_statuses(event_id)[0].occupied == 0
    p = store.get_person(p.id)
    assert all(b.status == "delivered" and b.delivered_at for b in p.bultos)
    assert store.deliver(p.id) == 0


def test_demo_limits(store):
    ev = store.create_event("Evento 1", default_zone_capacity=20)
    with pytest.raises(LimitError):
        store.create_event("Evento 2")
    for i in range(5):
        store.register(ev, f"Persona {i} Prueba", f"1000000{i}", ["x"])
    with pytest.raises(LimitError):
        store.register(ev, "Sexta Persona", "10000009", ["x"])
    # consultar y retirar sigue funcionando
    assert store.search(ev, "persona")
    p = store.search(ev, "persona 0")[0]
    assert store.deliver(p.id) == 1


def test_demo_limit_survives_delete(store, conn):
    store.create_event("Evento 1")
    conn.execute("DELETE FROM events")
    conn.commit()
    with pytest.raises(LimitError):
        store.create_event("Evento 2")


def test_search_performance(store, conn):
    ev = store.create_event("Grande", default_zone_capacity=999)
    # alta masiva directa para no pasar por los límites demo
    with conn:
        zid = conn.execute("SELECT id FROM zones WHERE event_id=?", (ev,)).fetchone()["id"]
        for i in range(5000):
            conn.execute(
                "INSERT INTO people(event_id,full_name,full_name_norm,dni,ticket_code) VALUES(?,?,?,?,?)",
                (ev, f"Persona {i}", f"persona {i}", f"{i:08d}", f"T{i:05d}"),
            )
    t = time.perf_counter()
    res = store.search(ev, "persona 4999")
    assert time.perf_counter() - t < 1
    assert res


def test_export_csv(store, event_id, tmp_path):
    store.register(event_id, "Ana Díaz", "12345678", ["a", "b"])
    n = store.export_csv(event_id, tmp_path / "x.csv")
    assert n == 2
