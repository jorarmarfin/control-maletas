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


def test_v2_key_roundtrip_and_whatsapp_wrapping(conn, private_key):
    from control_maletas.licensing import sign_key
    mgr = LicenseManager(conn, private_key.public_key())
    key = sign_key(payload(), private_key)
    assert key.startswith("CM2.")
    wrapped = "\n".join(key[i:i + 40] for i in range(0, len(key), 40))
    info = mgr.install("  " + wrapped + "\n")
    assert info.event == "Retiro Octubre"
    assert len(mgr.installed()) == 1


def test_v2_key_tampered_or_truncated(conn, private_key):
    from control_maletas.licensing import sign_key
    mgr = LicenseManager(conn, private_key.public_key())
    key = sign_key(payload(), private_key)
    head, p, s = key.split(".")
    bad_payload = payload(max_people=9999)
    import base64, json
    forged = base64.urlsafe_b64encode(json.dumps(bad_payload, separators=(",", ":")).encode()).decode().rstrip("=")
    with pytest.raises(LicenseError):
        mgr.install(f"{head}.{forged}.{s}")
    with pytest.raises(LicenseError):
        mgr.install(key[:-10])
    with pytest.raises(LicenseError):
        mgr.install("CM2.basura")


def test_lic_file_with_bom_and_extra_fields(conn, private_key):
    from control_maletas.licensing import sign_key
    mgr = LicenseManager(conn, private_key.public_key())
    key = sign_key(payload(product="cm", notes="x", version="1"), private_key)
    info = mgr.install("﻿" + key + "\r\n")  # .lic de Windows con BOM
    assert info.event == "Retiro Octubre"


FP = "ABCD-EFGH-IJKL-MNOP"


def _mgr(conn, private_key, fp=FP):
    return LicenseManager(conn, private_key.public_key(), fingerprint=fp)


def test_license_bound_to_this_machine_ok(conn, private_key):
    from control_maletas.licensing import sign_key
    mgr = _mgr(conn, private_key)
    key = sign_key(payload(type="master", event=None, id="m1", machine_id="abcd efgh-ijkl-mnop"), private_key)
    assert mgr.install(key).machine_id
    assert mgr.master() is not None


def test_license_bound_to_other_machine_rejected(conn, private_key):
    from control_maletas.licensing import sign_key
    mgr = _mgr(conn, private_key)
    key = sign_key(payload(type="master", event=None, id="m2", machine_id="ZZZZ-ZZZZ-ZZZZ-ZZZZ"), private_key)
    with pytest.raises(LicenseError, match="otro equipo"):
        mgr.install(key)
    assert mgr.installed() == []


def test_unbound_license_still_valid(conn, private_key):
    from control_maletas.licensing import sign_key
    mgr = _mgr(conn, private_key)
    mgr.install(sign_key(payload(type="master", event=None, id="m3"), private_key))
    assert mgr.master() is not None


def test_db_copied_to_other_machine_ignores_bound_license(conn, private_key):
    from control_maletas.licensing import sign_key
    key = sign_key(payload(type="master", event=None, id="m4", machine_id=FP), private_key)
    _mgr(conn, private_key).install(key)
    other = _mgr(conn, private_key, fp="QQQQ-QQQQ-QQQQ-QQQQ")
    assert other.master() is None  # la BD copiada a otro PC no hereda la licencia


def test_fingerprint_format_and_stability():
    import re
    from control_maletas import machine
    a, b = machine.machine_fingerprint(), machine.machine_fingerprint()
    assert a == b and re.fullmatch(r"[A-Z2-7]{4}(-[A-Z2-7]{4}){3}", a)
