"""Generación de ticket: QR, imagen para pantalla y PDF imprimible."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import qrcode
from PIL import Image
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .store import PersonRecord


def qr_payload(ticket_code: str) -> str:
    return f"CM:{ticket_code}"


def make_qr_image(ticket_code: str, box_size: int = 8) -> Image.Image:
    qr = qrcode.QRCode(border=2, box_size=box_size, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(qr_payload(ticket_code))
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def format_code(code: str) -> str:
    return f"{code[:3]}-{code[3:]}" if len(code) == 6 else code


def make_ticket_pdf(person: PersonRecord, event_name: str, path: str | Path) -> Path:
    """Ticket de 80 mm de ancho (compatible con impresora térmica o A4 en PDF)."""
    path = Path(path)
    bultos = person.stored or person.bultos
    width = 80 * mm
    height = (112 + 7 * len(bultos)) * mm
    c = canvas.Canvas(str(path), pagesize=(width, height))
    y = height - 8 * mm
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, y, "CONTROL MALETAS")
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, y, event_name[:40])
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, y, person.full_name[:34])
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, y, f"DNI {person.dni}")

    qr = make_qr_image(person.ticket_code, box_size=10)
    qr_size = 42 * mm
    from reportlab.lib.utils import ImageReader
    y -= qr_size + 3 * mm
    c.drawImage(ImageReader(qr), (width - qr_size) / 2, y, qr_size, qr_size)

    y -= 9 * mm
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, y, format_code(person.ticket_code))
    y -= 7 * mm
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, y, f"{len(bultos)} bulto(s)")
    for b in bultos:
        y -= 5.5 * mm
        label = f"{b.location or '-'}  {b.description}".strip()
        c.drawString(6 * mm, y, label[:40])
    y -= 8 * mm
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(width / 2, y, "Presente este ticket para retirar su equipaje")
    c.showPage()
    c.save()
    return path


def print_file(path: str | Path) -> None:
    """Imprime con el sistema (mejor esfuerzo); en Linux usa lp o abre el visor."""
    path = str(path)
    if sys.platform.startswith("win"):
        try:
            os.startfile(path, "print")  # type: ignore[attr-defined]
        except OSError:
            os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["lp", path])
    else:
        for cmd in (["lp", path], ["xdg-open", path]):
            try:
                subprocess.Popen(cmd)
                return
            except FileNotFoundError:
                continue
