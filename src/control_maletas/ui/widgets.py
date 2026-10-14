import customtkinter as ctk

from .. import theme as T


def font(size=14, weight="normal"):
    return ctk.CTkFont(family=T.FONT, size=size, weight=weight)


class Card(ctk.CTkFrame):
    def __init__(self, master, **kw):
        kw.setdefault("fg_color", T.CARD)
        kw.setdefault("corner_radius", 16)
        kw.setdefault("border_width", 1)
        kw.setdefault("border_color", T.BORDER)
        super().__init__(master, **kw)


def heading(master, text, size=22):
    return ctk.CTkLabel(master, text=text, font=font(size, "bold"), text_color=T.TEXT, anchor="w")


def muted(master, text, size=13, **kw):
    return ctk.CTkLabel(master, text=text, font=font(size), text_color=T.MUTED, anchor="w", **kw)


def label(master, text, size=14, weight="normal", **kw):
    return ctk.CTkLabel(master, text=text, font=font(size, weight), text_color=T.TEXT, anchor="w", **kw)


def primary_button(master, text, command, **kw):
    kw.setdefault("height", 42)
    kw.setdefault("font", font(14, "bold"))
    return ctk.CTkButton(master, text=text, command=command, **kw)


def accent_button(master, text, command, **kw):
    kw.setdefault("height", 46)
    kw.setdefault("font", font(15, "bold"))
    return ctk.CTkButton(master, text=text, command=command, fg_color=T.YELLOW,
                         hover_color=T.YELLOW_HOVER, text_color=T.NAVY, **kw)


def ghost_button(master, text, command, **kw):
    kw.setdefault("height", 36)
    kw.setdefault("font", font(13, "bold"))
    return ctk.CTkButton(master, text=text, command=command, fg_color="transparent",
                         border_width=2, border_color=T.BLUE, text_color=(T.BLUE, T.WHITE),
                         hover_color=T.CARD_ALT, **kw)


def field(master, caption, placeholder="", width=280, **kw):
    """Etiqueta + entrada apiladas. Devuelve (frame, entry)."""
    box = ctk.CTkFrame(master, fg_color="transparent")
    muted(box, caption).pack(anchor="w")
    entry = ctk.CTkEntry(box, placeholder_text=placeholder, width=width, height=40,
                         font=font(14), **kw)
    entry.pack(fill="x", pady=(2, 0))
    return box, entry


class Stat(ctk.CTkFrame):
    def __init__(self, master, caption, value="0", color=T.BLUE):
        super().__init__(master, fg_color=T.CARD_ALT, corner_radius=14)
        self.value = ctk.CTkLabel(self, text=value, font=font(30, "bold"), text_color=color)
        self.value.pack(padx=22, pady=(10, 0))
        muted(self, caption, 12).pack(padx=22, pady=(0, 10))

    def set(self, v):
        self.value.configure(text=str(v))


class AutoScrollFrame(ctk.CTkScrollableFrame):
    """CTkScrollableFrame que oculta la barra cuando el contenido cabe."""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self._bar_visible = True
        self._parent_canvas.bind("<Configure>", self._schedule, add="+")
        self.bind("<Configure>", self._schedule, add="+")
        self.after(50, self._toggle)

    def _schedule(self, _e=None):
        self.after_idle(self._toggle)

    def _toggle(self):
        try:
            need = self.winfo_reqheight() > self._parent_canvas.winfo_height() + 1
        except Exception:
            return
        if need and not self._bar_visible:
            self._scrollbar.grid()
            self._bar_visible = True
        elif not need and self._bar_visible:
            self._scrollbar.grid_remove()
            self._bar_visible = False
