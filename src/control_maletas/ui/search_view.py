import tkinter.messagebox as mb

import customtkinter as ctk

from .. import theme as T
from ..store import PersonRecord, clean_ticket_code
from ..tickets import format_code
from .ticket_dialog import TicketDialog
from .widgets import AutoScrollFrame, Card, font, ghost_button, heading, label, muted, primary_button


class SearchView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._job = None
        heading(self, "Buscar y retirar").pack(anchor="w", pady=(0, 12))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x")
        self.entry = ctk.CTkEntry(
            bar, height=52, font=font(18),
            placeholder_text="🔍  Nombre, DNI o código del ticket (el lector QR escribe aquí)")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", self._on_enter)
        self.only_stored = ctk.CTkSwitch(bar, text="Solo con equipaje en custodia",
                                         font=font(13), text_color=T.TEXT,
                                         command=self.refresh)
        self.only_stored.pack(side="left", padx=14)

        self.count = muted(self, "")
        self.count.pack(anchor="w", pady=(10, 4))
        self.results = AutoScrollFrame(self, fg_color="transparent")
        self.results.pack(fill="both", expand=True)

    def on_show(self):
        self.refresh()
        self.entry.focus_set()

    def _on_key(self, event=None):
        if event and event.keysym == "Return":
            return
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(180, self.refresh)

    def _on_enter(self, _event=None):
        """Flujo de lector QR: el código exacto abre la confirmación de entrega."""
        ev = self.app.store.active_event()
        raw = self.entry.get()
        if not ev or not raw.strip():
            return
        person = self.app.store.find_by_ticket(ev["id"], raw)
        if person and clean_ticket_code(raw) == person.ticket_code:
            self._deliver_all(person)
            self.entry.delete(0, "end")
            self.refresh()

    def refresh(self):
        self._job = None
        for w in self.results.winfo_children():
            w.destroy()
        ev = self.app.store.active_event()
        if not ev:
            self.count.configure(text="No hay un evento activo.")
            return
        people = self.app.store.search(ev["id"], self.entry.get())
        if self.only_stored.get():
            people = [p for p in people if p.stored]
        self.count.configure(text=f"{len(people)} resultado(s)")
        if not people:
            muted(self.results, "Sin resultados. Revise el nombre, DNI o código.", 15).pack(pady=40)
        for p in people:
            self._card(p)

    def _card(self, p: PersonRecord):
        card = Card(self.results)
        card.pack(fill="x", pady=5, padx=2)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 2))
        label(head, p.full_name, 16, "bold").pack(side="left")
        ctk.CTkLabel(head, text=format_code(p.ticket_code), font=font(16, "bold"),
                     text_color=T.BLUE).pack(side="right")
        extra = f"DNI {p.dni}" + (f"  ·  Tel. {p.phone}" if p.phone else "")
        muted(card, extra).pack(anchor="w", padx=16)
        if p.notes:
            muted(card, f"Obs.: {p.notes}", 12).pack(anchor="w", padx=16)

        for b in p.bultos:
            row = ctk.CTkFrame(card, fg_color=T.CARD_ALT, corner_radius=8)
            row.pack(fill="x", padx=16, pady=2)
            stored = b.status == "stored"
            ctk.CTkLabel(row, text=b.location or "-", font=font(14, "bold"), width=64,
                         text_color=T.ORANGE if stored else T.MUTED).pack(side="left", padx=6, pady=5)
            label(row, b.description or "Bulto", 13).pack(side="left")
            if stored:
                ghost_button(row, "Entregar", lambda b=b, p=p: self._deliver_one(p, b), width=80,
                             height=28).pack(side="right", padx=6, pady=3)
            else:
                muted(row, f"Entregado {b.delivered_at or ''}", 12).pack(side="right", padx=10)

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(8, 12))
        if p.stored:
            primary_button(actions, f"Entregar todo ({len(p.stored)})",
                           lambda p=p: self._deliver_all(p, confirm=True), width=170).pack(side="left")
        ghost_button(actions, "Ver ticket", lambda p=p: self._show_ticket(p)).pack(side="left", padx=8)

    # ---------------------------------------------------------- acciones
    def _deliver_all(self, p: PersonRecord, confirm=True):
        n = len(p.stored)
        if n == 0:
            self.app.notify(f"{p.full_name} no tiene equipaje en custodia.", "info")
            return
        if confirm and not mb.askyesno(
                "Confirmar entrega",
                f"¿Entregar {n} bulto(s) a {p.full_name} (DNI {p.dni})?", parent=self.app):
            return
        self.app.store.deliver(p.id)
        self.app.notify(f"Entregado: {n} bulto(s) a {p.full_name}.", "ok")
        self.app.refresh_status()
        self.refresh()

    def _deliver_one(self, p: PersonRecord, b):
        if mb.askyesno("Confirmar entrega",
                       f"¿Entregar «{b.description or 'bulto'}» ({b.location}) a {p.full_name}?",
                       parent=self.app):
            self.app.store.deliver(p.id, [b.id])
            self.app.notify("Bulto entregado.", "ok")
            self.app.refresh_status()
            self.refresh()

    def _show_ticket(self, p: PersonRecord):
        ev = self.app.store.active_event()
        TicketDialog(self.app, self.app.store.get_person(p.id), ev["name"])
