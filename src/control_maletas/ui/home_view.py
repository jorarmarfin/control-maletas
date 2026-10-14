import tkinter as tk
from datetime import datetime

import customtkinter as ctk

from .. import theme as T
from .widgets import (AutoScrollFrame, Card, Stat, accent_button, font, ghost_button,
                      heading, label, muted)
from .locations_view import _c
from ..tickets import format_code


class HomeView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))
        heading(top, "Inicio").pack(side="left")
        accent_button(top, "🧳  Registrar equipaje", lambda: app.show("register"),
                      width=200, height=40).pack(side="right")
        ghost_button(top, "🔍  Buscar / Retirar", lambda: app.show("search"),
                     width=170, height=40).pack(side="right", padx=10)
        self.body = AutoScrollFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

    def on_show(self):
        for w in self.body.winfo_children():
            w.destroy()
        store = self.app.store
        ev = store.active_event()
        if not ev:
            c = Card(self.body)
            c.pack(fill="x", pady=8)
            label(c, "Bienvenido a Control Maletas", 20, "bold").pack(anchor="w", padx=22, pady=(20, 4))
            muted(c, "Cree su primer evento para empezar a registrar equipaje.", 14).pack(
                anchor="w", padx=22)
            accent_button(c, "📅  Crear evento", lambda: self.app.show("events"), width=200).pack(
                anchor="w", padx=22, pady=(14, 20))
            return

        # ---- resumen del evento activo
        s = store.stats(ev["id"])
        zones = store.zone_statuses(ev["id"])
        cap = sum(z.capacity for z in zones)
        occ = sum(z.occupied for z in zones)
        lim = store.licenses.limits_for_event(ev["name"])
        head = Card(self.body)
        head.pack(fill="x", pady=6, padx=2)
        row = ctk.CTkFrame(head, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(14, 4))
        label(row, ev["name"], 18, "bold").pack(side="left")
        ctk.CTkLabel(row, text=f"  {lim.label}  ", font=font(12, "bold"), corner_radius=8,
                     text_color=T.WHITE if lim.licensed else T.NAVY,
                     fg_color=T.GREEN if lim.licensed else T.YELLOW).pack(side="right")
        stats = ctk.CTkFrame(head, fg_color="transparent")
        stats.pack(fill="x", padx=18, pady=(4, 8))
        pct = f"{round(100 * occ / cap)}%" if cap else "0%"
        quota = ""
        if lim.max_people is not None:
            quota = f" / {lim.max_people}"
        for caption, val, col in (
                ("Personas" + (" (cupo)" if quota else ""), f"{s['people']}{quota}", T.BLUE),
                ("En custodia", s["stored"], T.ORANGE),
                ("Entregados", s["delivered"], T.GREEN),
                ("Ubicaciones libres", cap - occ, T.BLUE),
                ("Ocupación", pct, T.ORANGE)):
            Stat(stats, caption, val, col).pack(side="left", padx=(0, 10))
        if lim.max_people is not None and s["people"] >= lim.max_people:
            ctk.CTkLabel(head, text="⚠ Cupo de personas agotado — active una licencia para continuar.",
                         font=font(13, "bold"), text_color=T.RED).pack(anchor="w", padx=18, pady=(0, 12))
        else:
            ctk.CTkFrame(head, height=6, fg_color="transparent").pack()

        # ---- personas por evento
        card = Card(self.body)
        card.pack(fill="x", pady=6, padx=2)
        label(card, "Personas por evento", 16, "bold").pack(anchor="w", padx=18, pady=(14, 6))
        rows = store.dashboard_events()
        peak = max([r["people"] for r in rows] + [1])
        for r in rows:
            line = ctk.CTkFrame(card, fg_color=T.CARD_ALT, corner_radius=10)
            line.pack(fill="x", padx=18, pady=3)
            name = r["name"] + ("  ● activo" if r["active"] else "")
            label(line, name, 14, "bold", width=280).pack(side="left", padx=12, pady=8)
            bar = ctk.CTkProgressBar(line, width=220, height=12)
            bar.pack(side="left", padx=8)
            bar.set(r["people"] / peak)
            muted(line, f"{r['people']} personas · {r['stored']} en custodia · "
                        f"{r['delivered']} entregados").pack(side="left", padx=8)
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

        # ---- dos columnas: pendientes y últimos registros
        cols = ctk.CTkFrame(self.body, fg_color="transparent")
        cols.pack(fill="x", pady=6)
        cols.grid_columnconfigure((0, 1), weight=1, uniform="c")
        self._pending(cols, ev["id"]).grid(row=0, column=0, sticky="nsew", padx=(2, 6))
        self._recent(cols, ev["id"]).grid(row=0, column=1, sticky="nsew", padx=(6, 2))

        # ---- actividad por hora + zonas
        self._hours(ev["id"])
        self._zones(zones)

    # ------------------------------------------------------------------
    def _pending(self, parent, event_id):
        card = Card(parent)
        label(card, "Más tiempo en custodia", 16, "bold").pack(anchor="w", padx=18, pady=(14, 6))
        items = self.app.store.oldest_pending(event_id)
        if not items:
            muted(card, "Sin equipaje pendiente de retiro.").pack(anchor="w", padx=18, pady=(0, 14))
        for p, since in items:
            line = ctk.CTkFrame(card, fg_color=T.CARD_ALT, corner_radius=10)
            line.pack(fill="x", padx=18, pady=3)
            label(line, p.full_name, 13, "bold").pack(side="left", padx=10, pady=7)
            muted(line, f"{len(p.stored)} bulto(s) · {self._ago(since)}", 12).pack(side="right", padx=10)
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()
        return card

    def _recent(self, parent, event_id):
        card = Card(parent)
        label(card, "Últimos registros", 16, "bold").pack(anchor="w", padx=18, pady=(14, 6))
        people = self.app.store.recent_people(event_id)
        if not people:
            muted(card, "Aún no hay registros.").pack(anchor="w", padx=18, pady=(0, 14))
        for p in people:
            line = ctk.CTkFrame(card, fg_color=T.CARD_ALT, corner_radius=10)
            line.pack(fill="x", padx=18, pady=3)
            label(line, p.full_name, 13, "bold").pack(side="left", padx=10, pady=7)
            ctk.CTkLabel(line, text=format_code(p.ticket_code), font=font(13, "bold"),
                         text_color=T.BLUE).pack(side="right", padx=10)
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()
        return card

    def _hours(self, event_id):
        counts = self.app.store.registrations_by_hour(event_id)
        card = Card(self.body)
        card.pack(fill="x", pady=6, padx=2)
        label(card, "Registros por hora del día", 16, "bold").pack(anchor="w", padx=18, pady=(14, 6))
        w, h, pad = 900, 110, 22
        cv = tk.Canvas(card, width=w, height=h + 22, bg=_c(T.CARD), highlightthickness=0)
        cv.pack(anchor="w", padx=18, pady=(0, 14))
        peak = max(counts + [1])
        slot = w / 24
        for hr, n in enumerate(counts):
            x0 = hr * slot + 6
            bh = (h - pad) * n / peak
            cv.create_rectangle(x0, h - bh, x0 + slot - 12, h,
                                fill=T.YELLOW if n else _c(T.CARD_ALT), outline="")
            if n:
                cv.create_text(x0 + (slot - 12) / 2, h - bh - 8, text=str(n),
                               fill=_c(T.TEXT), font=("Segoe UI", 9, "bold"))
            cv.create_text(x0 + (slot - 12) / 2, h + 11, text=f"{hr:02d}",
                           fill=_c(T.MUTED), font=("Segoe UI", 8))

    def _zones(self, zones):
        card = Card(self.body)
        card.pack(fill="x", pady=6, padx=2)
        label(card, "Ocupación por zona", 16, "bold").pack(anchor="w", padx=18, pady=(14, 6))
        for z in zones:
            line = ctk.CTkFrame(card, fg_color="transparent")
            line.pack(fill="x", padx=18, pady=3)
            label(line, f"{z.code} · {z.name}", 13, "bold", width=220).pack(side="left")
            bar = ctk.CTkProgressBar(line, height=12)
            bar.pack(side="left", fill="x", expand=True, padx=10)
            bar.set(z.occupied / z.capacity if z.capacity else 0)
            muted(line, f"{z.occupied}/{z.capacity}", 12).pack(side="left")
        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()

    @staticmethod
    def _ago(stamp: str) -> str:
        try:
            mins = int((datetime.now() - datetime.fromisoformat(stamp)).total_seconds() // 60)
        except (TypeError, ValueError):
            return ""
        if mins < 1:
            return "hace instantes"
        if mins < 60:
            return f"hace {mins} min"
        if mins < 1440:
            return f"hace {mins // 60} h {mins % 60} min"
        return f"hace {mins // 1440} d"
