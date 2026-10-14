"""Genera los PNG de logo que exige el manifiesto MSIX. Uso: make_assets.py <logo.png> <dir_salida>"""
import sys
from pathlib import Path

from PIL import Image

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
logo = Image.open(src).convert("RGBA")
for name, size in {"Square44x44Logo.png": (44, 44), "Square150x150Logo.png": (150, 150),
                   "StoreLogo.png": (50, 50)}.items():
    logo.resize(size, Image.LANCZOS).save(out / name)
wide = Image.new("RGBA", (310, 150), (10, 31, 92, 255))
wide.paste(logo.resize((140, 140), Image.LANCZOS), (85, 5))
wide.save(out / "Wide310x150Logo.png")
