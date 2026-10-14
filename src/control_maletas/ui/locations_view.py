import customtkinter as ctk

from .. import theme as T
from .widgets import AutoScrollFrame, Card, font, heading, label, muted


class LocationsView(ctk.CTkFrame):
    COLS = 10

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        heading(self, "Ubicaciones").pack(anchor="w", pady=(0, 4))
        legend = ctk.CTkFrame(self, fg_color="transparent")
        legend.pack(anchor="w", pady=(0, 8))
        for color, text in ((T.CARD_ALT, "Libre"), (T.YELLOW, "Ocupada")):
            ctk.CTkLabel(legend, text="  ", fg_color=color, corner_radius=4, width=18).pack(side="left")
            muted(legend, f" {text}   ").pack(side="left")
        self.body = AutoScrollFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

    def on_show(self):
        for w in self.body.winfo_children():
            w.destroy()
        ev = self.app.store.active_event()
        if not ev:
            muted(self.body, "No hay un evento activo.", 15).pack(pady=40)
            return
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
            grid = ctk.CTkFrame(card, fg_color="transparent")
            grid.pack(fill="x", padx=12, pady=(0, 12))
            for i, loc in enumerate(self.app.store.zone_locations(z.id)):
                busy = bool(loc["occupied"])
                cell = ctk.CTkButton(
                    grid, text=loc["label"], width=64, height=32, font=font(12, "bold"),
                    fg_color=T.YELLOW if busy else T.CARD_ALT,
                    hover_color=T.YELLOW_HOVER if busy else T.BORDER,
                    text_color=T.NAVY if busy else T.MUTED,
                    command=lambda l=loc: self.app.notify(
                        f"{l['label']}: {l['full_name'] or 'libre'}", "info"))
                cell.grid(row=i // self.COLS, column=i % self.COLS, padx=2, pady=2)
