"""Rutas de datos de usuario y de recursos empaquetados."""
import os
import sys
from pathlib import Path

APP_DIR_NAME = "ControlMaletas"


def data_dir() -> Path:
    override = os.environ.get("CONTROL_MALETAS_DATA")
    if override:
        base = Path(override)
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home())) / APP_DIR_NAME
    else:
        xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        base = Path(xdg) / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "maletas.db"


def backups_dir() -> Path:
    p = data_dir() / "backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def tickets_dir() -> Path:
    p = data_dir() / "tickets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def resource_path(rel: str) -> Path:
    """Ruta a un recurso, funciona en desarrollo y dentro de PyInstaller."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[2]
    return base / rel
