"""Punto de entrada para PyInstaller y ejecución directa."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from control_maletas.app import main  # noqa: E402

if __name__ == "__main__":
    main()
