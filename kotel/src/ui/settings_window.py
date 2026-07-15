"""Окно настроек приложения."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import customtkinter as ctk

from .theme import (
    ACCENT,
    ACCENT_HOVER,
    BG_CARD,
    BG_CARD_SOFT,
    BG_MAIN,
    BORDER,
    BORDER_GLOW,
    PAD,
    RADIUS,
    TABVIEW,
    TEXT,
    TEXT_MUTED,
    TEXT_ON_ACCENT,
    font,
)

if TYPE_CHECKING:
    from .app import HeatBalanceApp


class SettingsWindow:
    """Настройки + «О программе»."""

    def __init__(
        self,
        app: HeatBalanceApp,
        *,
        on_label_mode_change: Callable[[str], None],
    ) -> None:
        self._app = app
        self._on_label_mode_change = on_label_mode_change

        self.win = ctk.CTkToplevel(app)
        self.win.title("Настройки")
        self.win.geometry("480x380")
        self.win.minsize(440, 340)
        self.win.configure(fg_color=BG_MAIN)
        self.win.transient(app)
        self.win.grab_set()

        tabs = ctk.CTkTabview(self.win, **TABVIEW)
        tabs.pack(fill="both", expand=True, padx=PAD["lg"], pady=PAD["lg"])
        tabs.add("Интерфейс")
        tabs.add("О программе")

        self._build_interface_tab(tabs.tab("Интерфейс"))
        self._build_about_tab(tabs.tab("О программе"))

    def _build_interface_tab(self, tab: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            tab,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_GLOW,
            corner_radius=RADIUS["md"],
        )
        card.pack(fill="both", expand=True, padx=PAD["sm"], pady=PAD["sm"])

        ctk.CTkLabel(
            card,
            text="Параметры отображения",
            font=font("section"),
            text_color=TEXT,
            anchor="w",
        ).pack(anchor="w", padx=PAD["md"], pady=(PAD["md"], PAD["md"]))

        self._label_mode_var = ctk.StringVar(value=self._app._label_mode)
        ctk.CTkRadioButton(
            card,
            text="Полное отображение — символ, описание, единицы",
            variable=self._label_mode_var,
            value="full",
            font=font("label"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=BORDER,
            text_color=TEXT,
            command=self._apply_label_mode,
        ).pack(anchor="w", padx=PAD["md"], pady=PAD["xs"])
        ctk.CTkRadioButton(
            card,
            text="Краткое отображение — только символ и единицы",
            variable=self._label_mode_var,
            value="compact",
            font=font("label"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=BORDER,
            text_color=TEXT,
            command=self._apply_label_mode,
        ).pack(anchor="w", padx=PAD["md"], pady=(PAD["xs"], PAD["md"]))

    def _build_about_tab(self, tab: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            tab,
            fg_color=BG_CARD_SOFT,
            border_width=1,
            border_color=BORDER_GLOW,
            corner_radius=RADIUS["md"],
        )
        card.pack(fill="both", expand=True, padx=PAD["sm"], pady=PAD["sm"])

        ctk.CTkLabel(
            card,
            text=self._app.APP_TITLE,
            font=font("section"),
            text_color=TEXT,
        ).pack(anchor="w", padx=PAD["md"], pady=(PAD["md"], PAD["xs"]))
        ctk.CTkLabel(
            card,
            text=f"Версия {self._app.APP_VERSION}",
            font=font("label"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=PAD["md"])

        about = (
            "Программа по расчёту теплового баланса котла.\n\n"
            "Плагин «Свойства пара» — свойства воды и пара по IAPWS-IF97.\n\n"
            "Архитектура: расчётное ядро, справочники JSON, система плагинов."
        )
        ctk.CTkLabel(
            card,
            text=about,
            font=font("body"),
            text_color=TEXT,
            justify="left",
            wraplength=400,
            anchor="w",
        ).pack(anchor="w", padx=PAD["md"], pady=PAD["md"])

        ctk.CTkButton(
            card,
            text="Закрыть",
            width=120,
            height=34,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            command=self.win.destroy,
        ).pack(anchor="e", padx=PAD["md"], pady=(0, PAD["md"]))

    def _apply_label_mode(self) -> None:
        self._on_label_mode_change(self._label_mode_var.get())
