import shutil
import sys
from datetime import datetime

import customtkinter as ctk
from PIL import Image, ImageTk

from . import APP_NAME, __version__, paths, theme as T
from . import db
from .licensing import LicenseManager
from .store import Store
from .ui.events_view import EventsView
from .ui.home_view import HomeView
from .ui.license_view import LicenseView
from .ui.limit_dialog import LimitDialog
from .ui.locations_view import LocationsView
from .ui.register_view import RegisterView
from .ui.search_view import SearchView
from .ui.widgets import font

NAV = [
    ("home", "🏠  Inicio", HomeView),
    ("register", "🧳  Registrar", RegisterView),
    ("search", "🔍  Buscar / Retirar", SearchView),
    ("locations", "📍  Ubicaciones", LocationsView),
    ("events", "📅  Eventos", EventsView),
    ("license", "🔑  Licencia", LicenseView),
]


class App(ctk.CTk):
    def __init__(self, db_file=None):
        T.apply()
        super().__init__(fg_color=T.BG)
        self.title(f"{APP_NAME} {__version__}")
        self.geometry("1180x760")
        self.minsize(1000, 640)
        self.withdraw()  # evita ver la ventana armándose
        self._set_icon()

        self.conn = db.connect(db_file or paths.db_path())
        self.store = Store(self.conn, LicenseManager(self.conn))

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=22, pady=(18, 14))
        self.status_bar = ctk.CTkFrame(self, fg_color=T.CARD, corner_radius=0, height=36)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_lbl = ctk.CTkLabel(self.status_bar, text="", font=font(12), text_color=T.MUTED)
        self.status_lbl.pack(side="left", padx=16, pady=6)
        self.toast = ctk.CTkLabel(self.status_bar, text="", font=font(13, "bold"))
        self.toast.pack(side="right", padx=16)

        self.views = {}
        self._current = "home"
        for key, _, cls in NAV:
            v = cls(self.content, self)
            v.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.views[key] = v
        self.refresh_status()
        self.show("home")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.update_idletasks()
        self.deiconify()

    # -------------------------------------------------------------- UI
    def _set_icon(self):
        ico = paths.resource_path("assets/icon.ico")
        try:
            if sys.platform.startswith("win"):
                self.iconbitmap(str(ico))
            else:
                img = Image.open(paths.resource_path("assets/logo.png")).resize((128, 128))
                self._icon = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._icon)
        except Exception:
            pass

    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, fg_color=T.SIDEBAR, corner_radius=0, width=230)
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_propagate(False)
        logo = Image.open(paths.resource_path("assets/logo.png"))
        self._logo = ctk.CTkImage(light_image=logo, dark_image=logo, size=(150, 150))
        ctk.CTkLabel(bar, image=self._logo, text="").pack(pady=(22, 18))
        self.nav_buttons = {}
        for key, text, _ in NAV:
            b = ctk.CTkButton(bar, text=text, anchor="w", height=46, font=font(15, "bold"),
                              fg_color="transparent", hover_color="#143382",
                              text_color=T.WHITE, corner_radius=12,
                              command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[key] = b
        ctk.CTkLabel(bar, text=f"v{__version__}", text_color="#8DA2D8",
                     font=font(11)).pack(side="bottom", pady=(0, 14))
        self.theme_switch = ctk.CTkSwitch(bar, text="Modo oscuro", text_color=T.WHITE,
                                          font=font(12), command=self._toggle_theme)
        self.theme_switch.pack(side="bottom", pady=8)

    def _toggle_theme(self):
        ctk.set_appearance_mode("dark" if self.theme_switch.get() else "light")
        self.show(self._current)  # re-dibuja vistas con canvas (usan colores resueltos)

    def show(self, key):
        for k, b in self.nav_buttons.items():
            b.configure(fg_color=T.YELLOW if k == key else "transparent",
                        text_color=T.NAVY if k == key else T.WHITE,
                        hover_color=T.YELLOW_HOVER if k == key else "#143382")
        self._current = key
        view = self.views[key]
        view.tkraise()
        if hasattr(view, "on_show"):
            view.on_show()

    def refresh_status(self):
        ev = self.store.active_event()
        if not ev:
            self.status_lbl.configure(text="Sin evento activo — cree uno en «Eventos».")
            return
        s = self.store.stats(ev["id"])
        lim = self.store.licenses.limits_for_event(ev["name"])
        self.status_lbl.configure(
            text=f"Evento: {ev['name']}   |   {s['people']} personas · {s['stored']} bultos en custodia"
                 f"   |   {lim.label}")

    def notify(self, message: str, kind: str = "info"):
        color = {"ok": T.GREEN, "error": T.RED, "info": T.BLUE}.get(kind, T.BLUE)
        self.toast.configure(text=message, text_color=color)
        self.after(6000, lambda: self.toast.configure(text=""))

    def show_limit(self, message: str, demo: bool = True):
        """Aviso modal por exceder la versión demo o el máximo de la licencia."""
        self.notify(message, "error")
        LimitDialog(self, message, demo)

    def _on_close(self):
        try:
            self.conn.commit()
            stamp = datetime.now().strftime("%Y%m%d-%H%M")
            shutil.copy2(paths.db_path(), paths.backups_dir() / f"maletas-{stamp}.db")
            backups = sorted(paths.backups_dir().glob("maletas-*.db"))
            for old in backups[:-10]:
                old.unlink(missing_ok=True)
        except Exception:
            pass
        self.conn.close()
        self.destroy()


def main():
    App().mainloop()
