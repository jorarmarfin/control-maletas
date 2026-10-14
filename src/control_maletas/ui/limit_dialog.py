import customtkinter as ctk

from .. import theme as T
from .widgets import accent_button, font, ghost_button, label


class LimitDialog(ctk.CTkToplevel):
    """Aviso modal y bien visible: la acción excede la versión demo / la licencia."""

    def __init__(self, app, message: str, demo: bool = True):
        super().__init__(app)
        self.withdraw()
        self.app = app
        self.title("Función no disponible en la versión demo" if demo else "Límite de la licencia")
        self.configure(fg_color=T.CARD)
        self.resizable(False, False)

        band = ctk.CTkFrame(self, fg_color=T.ORANGE, corner_radius=0, height=10)
        band.pack(fill="x")
        ctk.CTkLabel(self, text="🔒", font=font(46)).pack(pady=(16, 0))
        ctk.CTkLabel(self, text="Límite de la versión demo alcanzado" if demo else "Límite de la licencia alcanzado",
                     font=font(20, "bold"), text_color=T.TEXT).pack(padx=34, pady=(4, 8))
        ctk.CTkLabel(self, text=message, font=font(14), text_color=T.TEXT,
                     wraplength=420, justify="center").pack(padx=34)
        ctk.CTkLabel(self, text="Sus datos están a salvo: puede seguir consultando y entregando equipaje.",
                     font=font(12), text_color=T.MUTED, wraplength=420,
                     justify="center").pack(padx=34, pady=(10, 0))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=22)
        accent_button(row, "🔑  Activar licencia", self._go_license, width=190).pack(side="left", padx=6)
        ghost_button(row, "Cerrar", self.destroy, width=100, height=46).pack(side="left", padx=6)

        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = app.winfo_rootx() + (app.winfo_width() - w) // 2
        y = app.winfo_rooty() + (app.winfo_height() - h) // 3
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        self.transient(app)
        self.deiconify()
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(50, self._modal)

    def _modal(self):
        self.lift()
        self.focus_force()
        try:
            self.grab_set()
        except Exception:
            pass

    def _go_license(self):
        self.grab_release()
        self.destroy()
        self.app.show("license")
