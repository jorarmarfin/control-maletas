import tkinter as tk

import customtkinter as ctk

from .. import theme as T
from .widgets import AutoScrollFrame, Card, font, heading, label, muted


def _c(pair):
    """Resuelve un color (claro, oscuro) según el modo actual."""
    return pair[1] if ctk.get_appearance_mode() == "Dark" else pair[0]


class ZoneGrid(tk.Canvas):
    """Cuadrícula de ubicaciones dibujada en un solo canvas (cientos de celdas sin lag)."""

    COLS, CW, CH, GAP = 10, 66, 32, 4

    def __init__(self, master, locations, on_click, bg):
        rows = (len(locations) + self.COLS - 1) // self.COLS
        w = self.COLS * (self.CW + self.GAP) + self.GAP
        h = rows * (self.CH + self.GAP) + self.GAP
        super().__init__(master, width=w, height=h, bg=bg, highlightthickness=0, bd=0)
        free_bg, busy_bg = _c(T.CARD_ALT), T.YELLOW
        free_fg, busy_fg = _c(T.MUTED), T.NAVY
        self._on_click = on_click
        self._locs = {}
        f = ("Segoe UI", 9, "bold")
        for i, loc in enumerate(locations):
            x = self.GAP + (i % self.COLS) * (self.CW + self.GAP)
            y = self.GAP + (i // self.COLS) * (self.CH + self.GAP)
            busy = bool(loc["occupied"])
            tag = f"c{i}"
            self.create_rectangle(x, y, x + self.CW, y + self.CH, outline="",
                                  fill=busy_bg if busy else free_bg, tags=(tag,))
            self.create_text(x + self.CW / 2, y + self.CH / 2, text=loc["label"], font=f,
                             fill=busy_fg if busy else free_fg, tags=(tag,))
            self._locs[tag] = loc
            self.tag_bind(tag, "<Button-1>", lambda e, t=tag: self._on_click(self._locs[t]))
            self.tag_bind(tag, "<Enter>", lambda e: self.configure(cursor="hand2"))
            self.tag_bind(tag, "<Leave>", lambda e: self.configure(cursor=""))


class LocationsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        heading(self, "Ubicaciones").pack(anchor="w", pady=(0, 4))
        legend = ctk.CTkFrame(self, fg_color="transparent")
        legend.pack(anchor="w", pady=(0, 8))
        for color, text in ((T.CARD_ALT, "Libre"), (T.YELLOW, "Ocupada")):
            ctk.CTkLabel(legend, text="  ", fg_color=color, corner_radius=4, width=18).pack(side="left")
            muted(legend, f" {text}   ").pack(side="left")
        self.info = ctk.CTkLabel(
            legend, text="Haga clic en una ubicación para ver quién la ocupa", font=font(14, "bold"),
            text_color=T.MUTED, fg_color="transparent", corner_radius=8)
        self.info.pack(side="left", padx=18)
        self.body = AutoScrollFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

    def _click(self, loc):
        who = loc["full_name"]
        if who:
            self.info.configure(text=f"  {loc['label']}  ·  {who}  ", text_color=T.NAVY, fg_color=T.YELLOW)
        else:
            self.info.configure(text=f"  {loc['label']}  ·  libre  ", text_color=T.NAVY, fg_color=T.CARD_ALT)

    def on_show(self):
        for w in self.body.winfo_children():
            w.destroy()
        ev = self.app.store.active_event()
        if not ev:
            muted(self.body, "No hay un evento activo.", 15).pack(pady=40)
            return
        card_bg = _c(T.CARD)
        for z in self.app.store.zone_statuses(ev["id"]):
            card = Card(self.body)
            card.pack(fill="x", pady=6, padx=2)
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=16, pady=(12, 4))
            label(head, f"Zona {z.code} · {z.name}", 16, "bold").pack(side="left")
            muted(head, f"{z.occupied}/{z.capacity} ocupadas · {z.free} libres").pack(side="right")
            bar = ctk.CTkProgressBar(card, height=10)
            bar.pack(fill="x", padx=16, pady=(0, 8))
            bar.set(z.occupied / z.capacity if z.capacity else 0)
            ZoneGrid(card, self.app.store.zone_locations(z.id), self._click, card_bg).pack(
                anchor="w", padx=12, pady=(0, 12))
