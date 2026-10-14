import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from control_maletas import db  # noqa: E402
from control_maletas.licensing import LicenseManager  # noqa: E402
from control_maletas.store import Store  # noqa: E402


@pytest.fixture()
def private_key():
    return Ed25519PrivateKey.generate()


@pytest.fixture()
def conn():
    c = db.connect(":memory:")
    yield c
    c.close()


@pytest.fixture()
def store(conn, private_key):
    mgr = LicenseManager(conn, public_key=private_key.public_key())
    return Store(conn, mgr)


@pytest.fixture()
def event_id(store):
    return store.create_event("Retiro Octubre", default_zone_capacity=10)
