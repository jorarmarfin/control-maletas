import tkinter.filedialog as fd
from datetime import date

import customtkinter as ctk

from .. import theme as T
from ..errors import AppError, LimitError
from .datepicker import DateField
from .widgets import AutoScrollFrame, Card, Stat, field, ghost_button, heading, label, muted, primary_button


class EventsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        heading(self, "Eventos y zonas").pack(anchor="w", pady=(0, 12))
        scroll = AutoScrollFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # nuevo evento
        c = Card(scroll)
        c.pack(fill="x", pady=6, padx=2)
        label(c, "Nuevo evento", 16, "bold").pack(anchor="w", padx=18, pady=(14, 4))
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 14))
        f, self.ev_name = field(row, "Nombre del evento", "Ej. Retiro de Semana Santa", width=320)
        f.pack(side="left", padx=(0, 10))
        self.ev_from = DateField(row, "Inicio", value=date.today())
        self.ev_from.pack(side="left", padx=(0, 10))
        self.ev_to = DateField(row, "Fin (opcional)")
        self.ev_to.pack(side="left", padx=(0, 10))
        primary_button(row, "Crear evento", self._create_event).pack(side="left", pady=(18, 0))

        self.events_box = Card(scroll)
        self.events_box.pack(fill="x", pady=6, padx=2)
        self.zones_box = Card(scroll)

    def on_show(self):
        self._render_events()
        self._render_zones()

    def _create_event(self):
        try:
            eid = self.app.store.create_event(
                self.ev_name.get(), self.ev_from.get() or None, self.ev_to.get() or None)
        except LimitError as exc:
            self.app.show_limit(str(exc), exc.demo)
            return
        except AppError as exc:
            self.app.notify(str(exc), "error")
            return
        self.ev_name.delete(0, "end")
        self.app.notify("Evento creado. Se creó la zona A con 50 ubicaciones.", "ok")
        self.app.refresh_status()
        self.on_show()

    def _render_events(self):
        for w in self.events_box.winfo_children():
            w.destroy()
        label(self.events_box, "Eventos", 16, "bold").pack(anchor="w", padx=18, pady=(14, 6))
        events = self.app.store.list_events()
        if not events:
            muted(self.events_box, "Todavía no hay eventos. Cree el primero arriba.").pack(
                anchor="w", padx=18, pady=(0, 14))
        for e in events:
            row = ctk.CTkFrame(self.events_box, fg_color=T.CARD_ALT, corner_radius=10)
            row.pack(fill="x", padx=18, pady=3)
            label(row, e["name"], 14, "bold").pack(side="left", padx=12, pady=8)
            muted(row, f"{e['starts_at'] or ''} → {e['ends_at'] or ''}").pack(side="left")
            if e["active"]:
                ctk.CTkLabel(row, text="ACTIVO", text_color=T.NAVY, fg_color=T.YELLOW,
                             corner_radius=8, font=ctk.CTkFont(size=11, weight="bold"),
                             width=70).pack(side="right", padx=10)
            else:
                ghost_button(row, "Activar", lambda i=e["id"]: self._activate(i),
                             width=80, height=28).pack(side="right", padx=10)
        ctk.CTkFrame(self.events_box, height=8, fg_color="transparent").pack()

    def _activate(self, event_id):
        self.app.store.set_active_event(event_id)
        self.app.refresh_status()
        self.on_show()

    def _render_zones(self):
        for w in self.zones_box.winfo_children():
            w.destroy()
        ev = self.app.store.active_event()
        if not ev:
            self.zones_box.pack_forget()
            return
        if not self.zones_box.winfo_ismapped():
            self.zones_box.pack(fill="x", pady=6, padx=2)
        label(self.zones_box, f"Zonas de «{ev['name']}»", 16, "bold").pack(
            anchor="w", padx=18, pady=(14, 6))
        for z in self.app.store.zone_statuses(ev["id"]):
            row = ctk.CTkFrame(self.zones_box, fg_color=T.CARD_ALT, corner_radius=10)
            row.pack(fill="x", padx=18, pady=3)
            label(row, f"{z.code} · {z.name}", 14, "bold").pack(side="left", padx=12, pady=8)
            muted(row, f"capacidad {z.capacity} · ocupadas {z.occupied}").pack(side="right", padx=12)
        add = ctk.CTkFrame(self.zones_box, fg_color="transparent")
        add.pack(fill="x", padx=18, pady=10)
        f, self.z_code = field(add, "Código", "B", width=80)
        f.pack(side="left", padx=(0, 10))
        f, self.z_name = field(add, "Nombre", "Segundo piso", width=220)
        f.pack(side="left", padx=(0, 10))
        f, self.z_cap = field(add, "Capacidad", "50", width=100)
        f.pack(side="left", padx=(0, 10))
        primary_button(add, "Agregar zona", self._add_zone).pack(side="left", pady=(18, 0))

        stats = self.app.store.stats(ev["id"])
        srow = ctk.CTkFrame(self.zones_box, fg_color="transparent")
        srow.pack(fill="x", padx=18, pady=(4, 16))
        for cap, val, col in (("Personas", stats["people"], T.BLUE),
                              ("En custodia", stats["stored"], T.ORANGE),
                              ("Entregados", stats["delivered"], T.GREEN)):
            Stat(srow, cap, val, col).pack(side="left", padx=(0, 10))
        ghost_button(srow, "Exportar CSV", self._export).pack(side="right")

    def _add_zone(self):
        ev = self.app.store.active_event()
        try:
            cap = int(self.z_cap.get() or 0)
            self.app.store.add_zone(ev["id"], self.z_code.get(), self.z_name.get(), cap)
        except ValueError:
            self.app.notify("La capacidad debe ser un número.", "error")
            return
        except AppError as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.notify("Zona agregada.", "ok")
        self.app.refresh_status()
        self._render_zones()

    def _export(self):
        ev = self.app.store.active_event()
        dest = fd.asksaveasfilename(parent=self.app, defaultextension=".csv",
                                    initialfile=f"{ev['name']}.csv", filetypes=[("CSV", "*.csv")])
        if dest:
            n = self.app.store.export_csv(ev["id"], dest)
            self.app.notify(f"Exportados {n} bultos.", "ok")
