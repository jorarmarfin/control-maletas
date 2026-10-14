"""Paleta tomada del logo: azul intenso, azul marino, amarillo y naranja."""
import customtkinter as ctk

BLUE = "#0B5ED7"
BLUE_HOVER = "#0A4DB3"
NAVY = "#0A1F5C"
NAVY_DEEP = "#071538"
YELLOW = "#FFC21A"
YELLOW_HOVER = "#E6AB00"
ORANGE = "#F7931E"
WHITE = "#FFFFFF"
GREEN = "#1F9D55"
RED = "#D64545"

# (claro, oscuro)
BG = ("#EEF3FB", "#0B1530")
CARD = ("#FFFFFF", "#142349")
CARD_ALT = ("#E3ECFA", "#1B2F5E")
TEXT = ("#0A1F5C", "#F2F5FC")
MUTED = ("#5B6B94", "#9FB0D6")
SIDEBAR = (NAVY, NAVY_DEEP)
BORDER = ("#CBD7EE", "#2B4180")

FONT = "Segoe UI"


def apply() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    t = ctk.ThemeManager.theme
    t["CTkButton"].update(fg_color=[BLUE, BLUE], hover_color=[BLUE_HOVER, BLUE_HOVER],
                          text_color=[WHITE, WHITE], corner_radius=10)
    t["CTkEntry"].update(border_color=list(BORDER), fg_color=["#FFFFFF", "#0F1B3D"],
                         text_color=list(TEXT), corner_radius=10)
    t["CTkProgressBar"].update(progress_color=[BLUE, YELLOW], fg_color=list(CARD_ALT))
    t["CTkScrollableFrame"].update(label_fg_color=list(CARD_ALT))
    t["CTkSwitch"].update(progress_color=[BLUE, YELLOW])
    t["CTkOptionMenu"].update(fg_color=[BLUE, BLUE], button_color=[BLUE_HOVER, BLUE_HOVER])
