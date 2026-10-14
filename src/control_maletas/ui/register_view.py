import customtkinter as ctk

from .. import theme as T
from ..errors import AppError
from ..store import DNI_RE
from .ticket_dialog import TicketDialog
from .widgets import AutoScrollFrame, Card, accent_button, font, field, ghost_button, heading, label, muted


class RegisterView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._existing = None
        self._bulto_rows = []

        heading(self, "Registrar equipaje").pack(anchor="w", pady=(0, 12))
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure((0, 1), weight=1, uniform="c")
        body.grid_rowconfigure(0, weight=1)

        # --- persona
        left = Card(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        label(left, "Datos de la persona", 16, "bold").pack(anchor="w", padx=20, pady=(18, 8))
        f, self.dni = field(left, "DNI (8 dígitos)", "12345678")
        f.pack(fill="x", padx=20, pady=4)
        self.dni.bind("<KeyRelease>", lambda e: self._check_dni())
        self.dni_info = ctk.CTkLabel(left, text="", font=font(12, "bold"), text_color=T.ORANGE,
                                     anchor="w", wraplength=380, justify="left")
        self.dni_info.pack(fill="x", padx=20)
        f, self.name = field(left, "Nombres y apellidos", "Ej. María López Quispe")
        f.pack(fill="x", padx=20, pady=4)
        f, self.phone = field(left, "Teléfono (opcional)", "999 999 999")
        f.pack(fill="x", padx=20, pady=4)
        f, self.notes = field(left, "Observaciones (opcional)", "")
        f.pack(fill="x", padx=20, pady=4)

        # --- equipaje
        right = Card(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        top = ctk.CTkFrame(right, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(18, 4))
        label(top, "Equipaje", 16, "bold").pack(side="left")
        self.free_lbl = muted(top, "")
        self.free_lbl.pack(side="right")
        self.rows_box = AutoScrollFrame(right, fg_color="transparent", height=230)
        self.rows_box.pack(fill="both", expand=True, padx=12, pady=4)
        ghost_button(right, "＋ Agregar bulto", self._add_row).pack(anchor="w", padx=20, pady=(4, 16))

        self.submit = accent_button(self, "Registrar y generar ticket", self._submit)
        self.submit.pack(fill="x", pady=(12, 0))
        self.reset()

    # ----------------------------------------------------------- bultos
    def _add_row(self, text=""):
        row = ctk.CTkFrame(self.rows_box, fg_color="transparent")
        row.pack(fill="x", pady=3)
        n = len(self._bulto_rows) + 1
        entry = ctk.CTkEntry(row, height=40, font=font(14),
                             placeholder_text=f"Bulto {n}: ej. maleta azul, mochila…")
        entry.pack(side="left", fill="x", expand=True)
        if text:
            entry.insert(0, text)
        btn = ctk.CTkButton(row, text="✕", width=36, height=36, fg_color=T.CARD_ALT,
                            text_color=T.TEXT, hover_color=T.BORDER,
                            command=lambda: self._remove_row(row))
        btn.pack(side="left", padx=(6, 0))
        self._bulto_rows.append((row, entry))
        entry.focus_set()

    def _remove_row(self, row):
        if len(self._bulto_rows) <= 1:
            return
        self._bulto_rows = [(r, e) for r, e in self._bulto_rows if r is not row]
        row.destroy()

    def _bultos(self):
        # cada fila cuenta como un bulto, aunque su descripción esté vacía
        return [e.get().strip() for _, e in self._bulto_rows]

    # ------------------------------------------------------------- dni
    def _check_dni(self):
        ev = self.app.store.active_event()
        dni = self.dni.get().strip()
        self._existing = None
        self.dni_info.configure(text="")
        self.name.configure(state="normal")
        if ev and DNI_RE.match(dni):
            found = self.app.store.find_by_dni(ev["id"], dni)
            if found:
                self._existing = found
                self.name.delete(0, "end")
                self.name.insert(0, found.full_name)
                self.name.configure(state="disabled")
                self.dni_info.configure(
                    text=f"Ya registrado ({found.ticket_code}). Los bultos nuevos se agregarán a su ticket.")
        self.submit.configure(
            text="Agregar bultos al ticket existente" if self._existing
            else "Registrar y generar ticket")

    # ---------------------------------------------------------- acciones
    def _submit(self):
        store, ev = self.app.store, self.app.store.active_event()
        if not ev:
            self.app.notify("Primero cree un evento.", "error")
            return
        try:
            if self._existing:
                person = store.add_bultos(self._existing.id, self._bultos())
            else:
                person = store.register(
                    ev["id"], self.name.get(), self.dni.get(), self._bultos(),
                    self.phone.get(), self.notes.get())
        except AppError as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.refresh_status()
        TicketDialog(self.app, person, ev["name"], on_close=self.reset)

    def reset(self):
        self._existing = None
        self.name.configure(state="normal")
        for w in (self.dni, self.name, self.phone, self.notes):
            if w.get():
                w.delete(0, "end")
        self.dni_info.configure(text="")
        for row, _ in self._bulto_rows:
            row.destroy()
        self._bulto_rows = []
        self._add_row()
        self.submit.configure(text="Registrar y generar ticket")
        self.dni.focus_set()
        self.on_show()

    def on_show(self):
        ev = self.app.store.active_event()
        if ev:
            free = sum(z.free for z in self.app.store.zone_statuses(ev["id"]))
            self.free_lbl.configure(text=f"{free} ubicaciones libres")
