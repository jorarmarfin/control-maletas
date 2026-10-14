import tkinter.filedialog as fd

import customtkinter as ctk

from .. import theme as T
from ..errors import AppError
from ..licensing import DEMO_MAX_EVENTS, DEMO_MAX_PEOPLE
from .widgets import Card, accent_button, heading, label, muted


class LicenseView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        heading(self, "Licencia").pack(anchor="w", pady=(0, 12))
        self.status = Card(self)
        self.status.pack(fill="x", pady=6)
        self.list_box = Card(self)
        self.list_box.pack(fill="x", pady=6)
        accent_button(self, "Activar licencia desde archivo (.lic)…", self._activate).pack(
            anchor="w", pady=12)

    def on_show(self):
        for w in self.status.winfo_children() + self.list_box.winfo_children():
            w.destroy()
        store = self.app.store
        ev = store.active_event()
        if ev:
            lim = store.licenses.limits_for_event(ev["name"])
            colour = T.GREEN if lim.licensed else T.ORANGE
            ctk.CTkLabel(self.status, text=("● " + lim.label), text_color=colour,
                         font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=18, pady=(14, 2))
            used = store.people_count(ev["id"])
            cap = "sin límite" if lim.max_people is None else f"{used} de {lim.max_people}"
            muted(self.status, f"Evento activo: {ev['name']} · personas registradas: {cap}").pack(
                anchor="w", padx=18, pady=(0, 14))
        else:
            muted(self.status, "Sin evento activo.").pack(anchor="w", padx=18, pady=14)
        if not store.licenses.master():
            muted(self.status,
                  f"Sin licencia: máximo {DEMO_MAX_EVENTS} evento y {DEMO_MAX_PEOPLE} personas registradas.").pack(
                anchor="w", padx=18, pady=(0, 14))

        label(self.list_box, "Licencias instaladas", 15, "bold").pack(anchor="w", padx=18, pady=(14, 6))
        lics = store.licenses.installed()
        if not lics:
            muted(self.list_box, "Ninguna.").pack(anchor="w", padx=18, pady=(0, 14))
        for l in lics:
            kind = "MAESTRA" if l.type == "master" else f"Evento: {l.event}"
            vig = f"{l.starts_at or '…'} → {l.ends_at or '…'}"
            mx = "" if l.max_people is None else f" · máx. {l.max_people} personas"
            row = ctk.CTkFrame(self.list_box, fg_color=T.CARD_ALT, corner_radius=10)
            row.pack(fill="x", padx=18, pady=3)
            label(row, kind, 14, "bold").pack(side="left", padx=12, pady=8)
            muted(row, f"{l.licensee or ''} · {vig}{mx}").pack(side="left")
        ctk.CTkFrame(self.list_box, height=10, fg_color="transparent").pack()

    def _activate(self):
        path = fd.askopenfilename(parent=self.app, title="Archivo de licencia",
                                  filetypes=[("Licencia", "*.lic"), ("Todos", "*.*")])
        if not path:
            return
        try:
            text = open(path, encoding="utf-8").read()
            info = self.app.store.licenses.install(text)
        except (AppError, OSError) as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.notify(f"Licencia activada: {info.type} {info.event or ''}".strip(), "ok")
        self.app.refresh_status()
        self.on_show()
