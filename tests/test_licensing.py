import json
from datetime import date

import pytest

from control_maletas.errors import LicenseError, LimitError
from control_maletas.licensing import LicenseManager, sign_license
from control_maletas.store import Store


def payload(**kw):
    base = {"id": "abc123", "type": "event", "event": "Retiro Octubre", "licensee": "Parroquia",
            "starts_at": "2026-01-01", "ends_at": "2099-12-31", "max_people": 3}
    base.update(kw)
    return base


def test_valid_license_installs(conn, private_key):
    mgr = LicenseManager(conn, private_key.public_key())
    info = mgr.install(sign_license(payload(), private_key))
    assert info.event == "Retiro Octubre"
    assert len(mgr.installed()) == 1


def test_tampered_signature_rejected(conn, private_key):
    mgr = LicenseManager(conn, private_key.public_key())
    doc = json.loads(sign_license(payload(), private_key))
    doc["payload"]["max_people"] = 9999
    with pytest.raises(LicenseError):
        mgr.install(json.dumps(doc))


def test_wrong_key_rejected(conn, private_key):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    mgr = LicenseManager(conn, private_key.public_key())
    with pytest.raises(LicenseError):
        mgr.install(sign_license(payload(), Ed25519PrivateKey.generate()))


def test_garbage_rejected(conn, private_key):
    with pytest.raises(LicenseError):
        LicenseManager(conn, private_key.public_key()).install("no es json")


def test_event_license_lifts_limit_only_for_its_event(conn, private_key):
    mgr = LicenseManager(conn, private_key.public_key())
    mgr.install(sign_license(payload(max_people=None), private_key))
    st = Store(conn, mgr)
    ev = st.create_event("Retiro Octubre", default_zone_capacity=20)
    for i in range(8):
        st.register(ev, f"Persona {i} Prueba", f"2000000{i}", ["x"])
    assert mgr.limits_for_event("Otro").max_people == 5


def test_event_license_max_people(conn, private_key):
    mgr = LicenseManager(conn, private_key.public_key())
    mgr.install(sign_license(payload(max_people=2), private_key))
    st = Store(conn, mgr)
    ev = st.create_event("Retiro Octubre", default_zone_capacity=20)
    st.register(ev, "Persona Uno", "20000001", ["x"])
    st.register(ev, "Persona Dos", "20000002", ["x"])
    with pytest.raises(LimitError):
        st.register(ev, "Persona Tres", "20000003", ["x"])


def test_expired_license_falls_back_to_demo(conn, private_key):
    mgr = LicenseManager(conn, private_key.public_key())
    mgr.install(sign_license(payload(ends_at="2020-01-01"), private_key))
    assert not mgr.limits_for_event("Retiro Octubre").licensed
    assert mgr.limits_for_event("Retiro Octubre", today=date(2019, 12, 31)).licensed is False  # aún no inicia


def test_master_license_no_limits(conn, private_key):
    mgr = LicenseManager(conn, private_key.public_key())
    mgr.install(sign_license(payload(type="master", event=None, id="m1", max_people=None), private_key))
    st = Store(conn, mgr)
    st.create_event("Uno", default_zone_capacity=20)
    st.create_event("Dos", default_zone_capacity=20)  # 2.º evento permitido
    ev = st.create_event("Tres", default_zone_capacity=20)
    for i in range(7):
        st.register(ev, f"Persona {i} Prueba", f"3000000{i}", ["x"])
    assert mgr.limits_for_event("Cualquiera").max_people is None


def test_second_event_allowed_with_matching_event_license(conn, private_key):
    mgr = LicenseManager(conn, private_key.public_key())
    st = Store(conn, mgr)
    st.create_event("Uno")
    with pytest.raises(LimitError):
        st.create_event("Retiro Octubre")
    mgr.install(sign_license(payload(), private_key))
    st.create_event("Retiro Octubre")
