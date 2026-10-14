import tkinter.filedialog as fd

import customtkinter as ctk

from .. import paths, theme as T
from ..store import PersonRecord
from ..tickets import format_code, make_qr_image, make_ticket_pdf, print_file
from .widgets import font, label, muted, primary_button, ghost_button, accent_button


class TicketDialog(ctk.CTkToplevel):
    def __init__(self, master, person: PersonRecord, event_name: str, on_close=None):
        super().__init__(master)
        self.title("Ticket de equipaje")
        self.configure(fg_color=T.BG)
        self.resizable(False, False)
        self.person, self.event_name, self._on_close = person, event_name, on_close
        self._pdf = None

        ctk.CTkLabel(self, text="✔  Equipaje registrado", font=font(20, "bold"),
                     text_color=T.GREEN).pack(pady=(18, 4), padx=30)
        label(self, person.full_name, 16, "bold").pack()
        muted(self, f"DNI {person.dni}").pack()

        qr = make_qr_image(person.ticket_code)
        self._qr = ctk.CTkImage(light_image=qr, dark_image=qr, size=(210, 210))
        ctk.CTkLabel(self, image=self._qr, text="", fg_color="white", corner_radius=8).pack(pady=12)

        ctk.CTkLabel(self, text=format_code(person.ticket_code), font=font(38, "bold"),
                     text_color=T.BLUE).pack()
        muted(self, "Código del ticket (también sirve para retirar)").pack(pady=(0, 8))

        for b in person.stored:
            row = ctk.CTkFrame(self, fg_color=T.CARD_ALT, corner_radius=10)
            row.pack(fill="x", padx=30, pady=2)
            ctk.CTkLabel(row, text=b.location or "-", font=font(15, "bold"),
                         text_color=T.ORANGE, width=70).pack(side="left", padx=8, pady=6)
            label(row, b.description or "Bulto", 13).pack(side="left", pady=6)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=18, padx=30, fill="x")
        accent_button(btns, "🖨  Imprimir", self._print, width=140).pack(side="left", padx=4)
        ghost_button(btns, "Guardar PDF", self._save_pdf, width=120).pack(side="left", padx=4)
        primary_button(btns, "Listo", self._close, width=90).pack(side="right", padx=4)

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(120, self._modal)

    def _modal(self):
        self.transient(self.master)
        self.lift()
        self.focus_force()
        try:
            self.grab_set()
        except Exception:
            pass

    def _ensure_pdf(self):
        if self._pdf is None:
            self._pdf = make_ticket_pdf(
                self.person, self.event_name,
                paths.tickets_dir() / f"ticket-{self.person.ticket_code}.pdf")
        return self._pdf

    def _print(self):
        print_file(self._ensure_pdf())

    def _save_pdf(self):
        dest = fd.asksaveasfilename(parent=self, defaultextension=".pdf",
                                    initialfile=f"ticket-{self.person.ticket_code}.pdf",
                                    filetypes=[("PDF", "*.pdf")])
        if dest:
            make_ticket_pdf(self.person, self.event_name, dest)

    def _close(self):
        self.grab_release()
        self.destroy()
        if self._on_close:
            self._on_close()
