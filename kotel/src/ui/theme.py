"""Тема: промышленный high-tech минимализм (тёмная инженерная палитра)."""

from __future__ import annotations

import customtkinter as ctk

# ── Фон ──────────────────────────────────────────────────────────────────
BG_APP = "#0b1220"
BG_SIDEBAR = "#0f172a"
BG_MAIN = "#111827"
BG_HEADER = "#0f1a2e"
BG_FOOTER = "#0a101c"
BG_CARD = "#1a2332"
BG_CARD_SOFT = "#151e2c"
BG_CARD_HOVER = "#1e293b"
BG_INPUT = "#0f172a"
BG_METRIC = "#1a2332"
BG_METRIC_SOFT = "#151e2c"
BG_BADGE = "#1e293b"
BG_BADGE_ACTIVE = "#f97316"
BG_ELEVATED = "#1e293b"
BG_SURFACE = "#162032"

# ── Акценты ──────────────────────────────────────────────────────────────
# Оранжевый — температура / мощность / КПД
ACCENT = "#f97316"
ACCENT_HOVER = "#ea580c"
ACCENT_SOFT = "#7c3a1a"
ACCENT_GLOW = "#fb923c"
ACCENT_MUTED = "#c2410c"

# Голубой — давление / пар / энтальпия
CYAN = "#22d3ee"
CYAN_HOVER = "#06b6d4"
CYAN_SOFT = "#0e4a5c"
CYAN_GLOW = "#67e8f9"
CYAN_MUTED = "#0891b2"

# ── Текст и границы ───────────────────────────────────────────────────────
TEXT = "#e2e8f0"
TEXT_MUTED = "#94a3b8"
TEXT_DIM = "#64748b"
TEXT_ON_ACCENT = "#0b1220"
TEXT_ON_CYAN = "#0b1220"
BORDER = "#334155"
BORDER_LIGHT = "#1e293b"
BORDER_GLOW = "#3d4f66"
BORDER_ACCENT = "#7c3a1a"
BORDER_CYAN = "#0e4a5c"

SUCCESS = "#34d399"
WARNING = "#fbbf24"
ERROR = "#f87171"

# ── Кнопки ───────────────────────────────────────────────────────────────
BTN_SECONDARY = {
    "fg_color": BG_CARD,
    "hover_color": BG_CARD_HOVER,
    "border_width": 1,
    "border_color": BORDER,
    "text_color": TEXT,
}

BTN_APPLY = {
    "fg_color": BG_CARD,
    "hover_color": CYAN_SOFT,
    "border_width": 1,
    "border_color": CYAN,
    "text_color": TEXT,
}

BTN_PRIMARY = {
    "fg_color": ACCENT,
    "hover_color": ACCENT_HOVER,
    "text_color": TEXT_ON_ACCENT,
}

BTN_CYAN = {
    "fg_color": CYAN,
    "hover_color": CYAN_HOVER,
    "text_color": TEXT_ON_CYAN,
}

BTN_UTILITY = BTN_SECONDARY

TABVIEW = {
    "fg_color": "transparent",
    "segmented_button_fg_color": BG_CARD_SOFT,
    "segmented_button_selected_color": ACCENT,
    "segmented_button_selected_hover_color": ACCENT_HOVER,
    "segmented_button_unselected_color": BG_CARD,
    "segmented_button_unselected_hover_color": BG_CARD_HOVER,
    "text_color": TEXT,
}

OPTION_MENU = {
    "fg_color": BG_INPUT,
    "button_color": CYAN_MUTED,
    "button_hover_color": CYAN,
    "dropdown_fg_color": BG_CARD,
    "dropdown_hover_color": BG_CARD_HOVER,
    "dropdown_text_color": TEXT,
    "text_color": TEXT,
}

FONT_FAMILY = "Segoe UI"

PAD = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
}

RADIUS = {
    "sm": 6,
    "md": 10,
    "lg": 14,
}

NAV_SECTIONS = [
    ("Топливо", "fuel", "01"),
    ("Уходящие газы", "flue", "02"),
    ("Котёл", "boiler", "03"),
    ("Полезное тепло", "useful", "04"),
    ("Расход топлива", "consumption", "05"),
    ("Результаты", "results", "06"),
]

INPUT_TABS = {"fuel", "flue", "boiler", "useful", "consumption"}

SCROLLBAR = {
    "scrollbar_button_color": BORDER,
    "scrollbar_button_hover_color": CYAN_MUTED,
}

# Matplotlib / графики
MPL_FACE = BG_CARD
MPL_AXES = BG_MAIN
MPL_GRID = "#1e293b"
MPL_TEXT = TEXT_MUTED
MPL_SPINE = BORDER

_font_cache: dict[str, ctk.CTkFont] = {}


def apply_theme() -> None:
    """Тёмный режим — промышленный HMI."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")


def font(name: str) -> ctk.CTkFont:
    if name not in _font_cache:
        specs = {
            "title": (18, "bold"),
            "subtitle": (13, "normal"),
            "section": (15, "bold"),
            "label": (13, "normal"),
            "value": (13, "bold"),
            "metric": (28, "bold"),
            "metric_unit": (12, "normal"),
            "nav": (13, "normal"),
            "nav_active": (13, "bold"),
            "body": (13, "normal"),
            "small": (11, "normal"),
            "mono": (12, "normal"),
            "brand": (16, "bold"),
            "step": (11, "bold"),
        }
        size, weight = specs.get(name, (13, "normal"))
        family = "Consolas" if name == "mono" else FONT_FAMILY
        _font_cache[name] = ctk.CTkFont(family=family, size=size, weight=weight)
    return _font_cache[name]

