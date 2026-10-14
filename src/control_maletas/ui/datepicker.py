"""Selector de fecha propio (sin dependencias) con el tema de la app."""
import calendar
from datetime import date

import customtkinter as ctk

from .. import theme as T
from .widgets import font, muted

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


class DateField(ctk.CTkFrame):
    """Etiqueta + entrada de fecha ISO (AAAA-MM-DD) + botón que abre el calendario."""

    def __init__(self, master, caption, width=170, value: date | None = None):
        super().__init__(master, fg_color="transparent")
        muted(self, caption).pack(anchor="w")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(2, 0))
        self.entry = ctk.CTkEntry(row, width=width - 46, height=40, font=font(14),
                                  placeholder_text="AAAA-MM-DD")
        self.entry.pack(side="left")
        ctk.CTkButton(row, text="📅", width=40, height=40, font=font(16),
                      fg_color=T.YELLOW, hover_color=T.YELLOW_HOVER, text_color=T.NAVY,
                      command=self._open).pack(side="left", padx=(6, 0))
        if value:
            self.set(value)

    def get(self) -> str:
        return self.entry.get().strip()

    def set(self, d: date | None) -> None:
        self.entry.delete(0, "end")
        if d:
            self.entry.insert(0, d.isoformat())

    def _current(self) -> date:
        try:
            return date.fromisoformat(self.get())
        except ValueError:
            return date.today()

    def _open(self):
        DatePopup(self, self._current(), self.set)


class DatePopup(ctk.CTkToplevel):
    def __init__(self, anchor, initial: date, on_pick):
        super().__init__(anchor)
        self.withdraw()  # se muestra recién al estar construida y posicionada
        self.title("Seleccionar fecha")
        self.configure(fg_color=T.CARD)
        self.resizable(False, False)
        self.on_pick, self.selected = on_pick, initial
        self.year, self.month = initial.year, initial.month

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(12, 4))
        self._nav(head, "‹", -1).pack(side="left")
        self.title_lbl = ctk.CTkLabel(head, text="", font=font(15, "bold"), text_color=T.TEXT)
        self.title_lbl.pack(side="left", expand=True)
        self._nav(head, "›", 1).pack(side="right")

        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(padx=12, pady=4)

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkButton(foot, text="Hoy", width=70, height=32, command=lambda: self._pick(date.today())
                      ).pack(side="left")
        ctk.CTkButton(foot, text="Limpiar", width=70, height=32, fg_color=T.CARD_ALT,
                      text_color=T.TEXT, hover_color=T.BORDER,
                      command=lambda: self._pick(None)).pack(side="right")

        self._render()
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 4
        x = max(0, min(x, self.winfo_screenwidth() - w))
        if y + h > self.winfo_screenheight():  # no cabe abajo: abrir hacia arriba
            y = max(0, anchor.winfo_rooty() - h - 4)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.transient(anchor.winfo_toplevel())
        self.deiconify()
        self.after(50, self._modal)

    def _modal(self):
        self.lift()
        self.focus_force()
        try:
            self.grab_set()
        except Exception:
            pass

    def _nav(self, parent, text, delta):
        return ctk.CTkButton(parent, text=text, width=34, height=32, font=font(18, "bold"),
                             fg_color=T.CARD_ALT, text_color=T.TEXT, hover_color=T.BORDER,
                             command=lambda: self._shift(delta))

    def _shift(self, delta):
        m = self.month - 1 + delta
        self.year += m // 12
        self.month = m % 12 + 1
        self._render()

    def _render(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.title_lbl.configure(text=f"{MESES[self.month - 1]} {self.year}")
        for c, d in enumerate(DIAS):
            ctk.CTkLabel(self.grid_frame, text=d, width=38, font=font(12, "bold"),
                         text_color=T.MUTED).grid(row=0, column=c, pady=(0, 2))
        today = date.today()
        for r, week in enumerate(calendar.Calendar(firstweekday=0).monthdayscalendar(
                self.year, self.month), start=1):
            for c, day in enumerate(week):
                if not day:
                    continue
                d = date(self.year, self.month, day)
                sel = d == self.selected
                ctk.CTkButton(
                    self.grid_frame, text=str(day), width=38, height=34, font=font(13, "bold" if sel else "normal"),
                    corner_radius=8,
                    fg_color=T.BLUE if sel else "transparent",
                    text_color=T.WHITE if sel else (T.ORANGE if d == today else T.TEXT),
                    hover_color=T.BLUE_HOVER if sel else T.CARD_ALT,
                    command=lambda d=d: self._pick(d),
                ).grid(row=r, column=c, padx=1, pady=1)

    def _pick(self, d):
        self.on_pick(d)
        self.grab_release()
        self.destroy()
