"""Главное окно приложения."""

from __future__ import annotations

import json
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from ..core.heat_balance import HeatBalanceCalculator
from ..core.models import (
    AshLosses,
    BoilerParams,
    FlueGasParams,
    FuelConsumptionParams,
    FuelProperties,
    FuelType,
    HeatBalanceInput,
    HeatBalanceResult,
    UsefulHeatParams,
)
from ..data.providers import JsonFileDataProvider
from ..plugins.registry import PluginRegistry
from .theme import (
    ACCENT,
    ACCENT_HOVER,
    BG_APP,
    BG_CARD,
    BG_CARD_HOVER,
    BG_FOOTER,
    BG_HEADER,
    BG_MAIN,
    BG_SIDEBAR,
    BORDER,
    BORDER_GLOW,
    BTN_SECONDARY,
    CYAN,
    CYAN_HOVER,
    INPUT_TABS,
    NAV_SECTIONS,
    PAD,
    RADIUS,
    TEXT,
    TEXT_DIM,
    TEXT_MUTED,
    TEXT_ON_ACCENT,
    apply_theme,
    font,
)
from . import notation as N
from .settings_store import load_settings, save_settings
from .settings_window import SettingsWindow
from .widgets import (
    DataTable,
    InfoBox,
    LabeledEntry,
    LossChart,
    MetricCard,
    NavButton,
    PageHeader,
    ResultRow,
    SectionFrame,
    make_scrollable_tab,
)
from .logo import attach_logo


class HeatBalanceApp(ctk.CTk):
    """Приложение расчёта теплового баланса котла."""

    APP_TITLE = "Тепловой баланс котла"
    APP_VERSION = "1.0.0"

    def __init__(
        self,
        project_root: Path,
        data_provider: JsonFileDataProvider | None = None,
        plugin_registry: PluginRegistry | None = None,
    ) -> None:
        super().__init__()

        self.project_root = project_root
        self.data_provider = data_provider or JsonFileDataProvider(
            project_root / "data" / "reference"
        )
        self.plugin_registry = plugin_registry or PluginRegistry()
        self.calculator = HeatBalanceCalculator(self.data_provider, self.plugin_registry)
        self._last_result: HeatBalanceResult | None = None
        self._last_input_tab: str = "fuel"
        self._current_tab: str = "fuel"
        self._current_fuel_preset_id: str | None = None
        self._fuel_entries: dict[str, LabeledEntry] = {}
        self._all_entries: list[LabeledEntry] = []
        self._result_rows: dict[str, ResultRow] = {}
        self._metric_cards: dict[str, MetricCard] = {}
        self._logo_image: object | None = None
        self._settings = load_settings(project_root)
        self._label_mode: str = self._settings.get("label_mode", "full")
        self._nav_menu: ctk.CTkToplevel | None = None
        self._settings_win: SettingsWindow | None = None
        self._loss_chart: LossChart | None = None
        self._results_table: DataTable | None = None
        self._transition_job: str | None = None

        apply_theme()

        self.title(f"{self.APP_TITLE} — v{self.APP_VERSION}")
        self.geometry("1280x820")
        self.minsize(1100, 720)
        self.resizable(True, True)
        self.configure(fg_color=BG_APP)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_main_area()
        self._build_footer()
        self._populate_fuel_presets()
        self._show_tab("fuel")

    def _update_dimensions_event(self, event=None) -> None:
        """Отключён тяжёлый обработчик CTk — он вызывается при каждом пикселе перетаскивания."""
        return

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, height=64, corner_radius=0, fg_color=BG_HEADER, border_width=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)
        header.grid_rowconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=1)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        # sticky="w" — слева по горизонтали, по центру по вертикали
        brand.grid(row=0, column=0, sticky="w", padx=PAD["lg"])

        self._menu_btn = ctk.CTkButton(
            brand,
            text="☰",
            width=36,
            height=36,
            corner_radius=RADIUS["sm"],
            font=font("section"),
            command=self._toggle_nav_menu,
            **BTN_SECONDARY,
        )
        self._menu_btn.pack(side="left", padx=(0, PAD["sm"]))

        logo_path = self.project_root / "assets" / "logo_header.png"
        self._logo_image = attach_logo(brand, logo_path, size=(34, 40))

        ctk.CTkLabel(
            brand,
            text=self.APP_TITLE,
            font=font("brand"),
            text_color=TEXT,
            anchor="w",
        ).pack(side="left", padx=(PAD["sm"], 0))

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e", padx=PAD["lg"])

        self.calc_btn = ctk.CTkButton(
            actions,
            text="Рассчитать",
            width=130,
            height=36,
            corner_radius=RADIUS["sm"],
            font=font("label"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            command=self._on_calculate,
        )
        self.calc_btn.pack(side="left")

        line = ctk.CTkFrame(self, height=1, fg_color=BORDER_GLOW, corner_radius=0)
        line.grid(row=0, column=0, columnspan=2, sticky="sew")

    def _toggle_nav_menu(self) -> None:
        if self._nav_menu is not None and self._nav_menu.winfo_exists():
            self._close_nav_menu()
            return

        menu = ctk.CTkToplevel(self)
        menu.wm_overrideredirect(True)
        menu.configure(fg_color=BG_MAIN)
        menu.attributes("-topmost", True)
        self._nav_menu = menu

        outer = ctk.CTkFrame(
            menu,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_GLOW,
            corner_radius=RADIUS["md"],
        )
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        def add_section(title: str) -> None:
            ctk.CTkLabel(
                outer,
                text=title.upper(),
                font=font("small"),
                text_color=CYAN,
                anchor="w",
            ).pack(fill="x", padx=PAD["md"], pady=(PAD["sm"], PAD["xs"]))

        def add_item(text: str, command) -> None:
            ctk.CTkButton(
                outer,
                text=text,
                anchor="w",
                height=32,
                font=font("label"),
                fg_color="transparent",
                hover_color=BG_CARD_HOVER,
                text_color=TEXT,
                command=lambda: self._run_menu_command(command),
            ).pack(fill="x", padx=PAD["xs"], pady=1)

        add_section("Расчёт")
        add_item("Сохранить…", self._save_json)
        add_item("Загрузить…", self._load_json)

        utilities = self.plugin_registry.utility_plugins()
        if utilities:
            add_section("Плагины")
            for plugin in utilities:
                add_item(plugin.get_menu_label(), lambda p=plugin: p.open_window(self))

        add_section("Приложение")
        add_item("Настройки…", self._open_settings)

        menu.update_idletasks()
        x = self._menu_btn.winfo_rootx()
        y = self._menu_btn.winfo_rooty() + self._menu_btn.winfo_height() + 4
        menu.geometry(f"240x{outer.winfo_reqheight() + 4}+{x}+{y}")
        menu.bind("<FocusOut>", lambda _e: self.after(150, self._close_nav_menu_if_unfocused))
        menu.focus_force()

    def _run_menu_command(self, command) -> None:
        self._close_nav_menu()
        command()

    def _close_nav_menu_if_unfocused(self) -> None:
        if self._nav_menu is None or not self._nav_menu.winfo_exists():
            return
        try:
            focused = self._nav_menu.focus_get()
        except Exception:
            focused = None
        if focused is None:
            self._close_nav_menu()

    def _close_nav_menu(self) -> None:
        if self._nav_menu is not None and self._nav_menu.winfo_exists():
            self._nav_menu.destroy()
        self._nav_menu = None

    def _open_settings(self) -> None:
        self._close_nav_menu()
        if self._settings_win is not None:
            try:
                if self._settings_win.win.winfo_exists():
                    self._settings_win.win.focus_force()
                    return
            except Exception:
                pass
        self._settings_win = SettingsWindow(self, on_label_mode_change=self._set_label_mode)

    def _set_label_mode(self, mode: str) -> None:
        if mode not in ("full", "compact"):
            mode = "full"
        self._label_mode = mode
        self._settings["label_mode"] = mode
        save_settings(self.project_root, self._settings)
        for entry in self._all_entries:
            entry.set_label_mode(self._label_mode)

    def _toggle_label_mode(self) -> None:
        # совместимость со старым переключателем (если вдруг вызовут)
        new_mode = "compact" if self._label_mode == "full" else "full"
        self._set_label_mode(new_mode)

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=248, corner_radius=0, fg_color=BG_SIDEBAR)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(1, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=PAD["md"], pady=(PAD["lg"], PAD["sm"]))
        ctk.CTkLabel(
            brand,
            text="Шаги расчёта",
            font=font("section"),
            text_color=TEXT,
            anchor="w",
        ).pack(anchor="w")

        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.grid(row=1, column=0, sticky="nsew", padx=PAD["sm"], pady=(PAD["xs"], PAD["md"]))
        nav_frame.grid_columnconfigure(0, weight=1)

        self._section_buttons: dict[str, NavButton] = {}
        for label, key, step in NAV_SECTIONS:
            btn = NavButton(nav_frame, label=label, step=step, command=lambda k=key: self._show_tab(k))
            btn.pack(fill="x", pady=1)
            self._section_buttons[key] = btn

        edge = ctk.CTkFrame(sidebar, width=1, fg_color=BORDER_GLOW)
        edge.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, height=36, corner_radius=0, fg_color=BG_FOOTER)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_rowconfigure(0, weight=1)
        footer.grid_columnconfigure(0, weight=1)

        status = ctk.CTkFrame(footer, fg_color="transparent")
        # sticky="w" — слева, по вертикали по центру полосы статуса
        status.grid(row=0, column=0, sticky="w", padx=PAD["lg"])

        self._status_dot = ctk.CTkLabel(
            status,
            text="●",
            font=font("small"),
            text_color=CYAN,
            width=16,
        )
        self._status_dot.pack(side="left")

        self.status_label = ctk.CTkLabel(
            status,
            text="Готово к расчёту",
            font=font("small"),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.status_label.pack(side="left", padx=(PAD["xs"], 0))

    def _build_main_area(self) -> None:
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_MAIN)
        self.main.grid(row=1, column=1, sticky="nsew")
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self.tabs: dict[str, ctk.CTkFrame] = {}
        self._build_fuel_tab()
        self._build_flue_tab()
        self._build_boiler_tab()
        self._build_useful_tab()
        self._build_consumption_tab()
        self._build_results_tab()

    def _add_entry(
        self,
        parent: ctk.CTkFrame,
        key: str,
        symbol: str,
        description: str,
        default: str,
        storage: dict[str, LabeledEntry],
        unit: str = "",
        tooltip: str = "",
    ) -> LabeledEntry:
        entry = LabeledEntry(
            parent,
            symbol=symbol,
            description=description,
            unit=unit,
            default=default,
            tooltip=tooltip,
            label_mode=self._label_mode,
        )
        entry.pack(fill="x", pady=4)
        storage[key] = entry
        self._all_entries.append(entry)
        return entry

    def _build_fuel_tab(self) -> None:
        tab = ctk.CTkFrame(self.main, fg_color="transparent")
        self.tabs["fuel"] = tab
        scroll = make_scrollable_tab(tab)

        PageHeader(
            scroll,
            "Топливо и зола",
            "Справочные свойства топлива и доли шлака / уноса",
        ).pack(fill="x", pady=(0, PAD["md"]))

        preset_sec = SectionFrame(
            scroll,
            title="Справочник топлива",
            subtitle="Выберите вид — поля заполнятся автоматически",
            glow="orange",
        )
        preset_sec.pack(fill="x", pady=(0, PAD["md"]))
        self.fuel_preset = ctk.CTkComboBox(
            preset_sec.body,
            values=["—"],
            command=self._on_fuel_preset,
            height=36,
            corner_radius=RADIUS["sm"],
            font=font("label"),
            dropdown_font=font("label"),
            fg_color=BG_CARD,
            border_color=BORDER,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=BG_CARD,
            dropdown_hover_color=BG_CARD_HOVER,
            text_color=TEXT,
        )
        self.fuel_preset.pack(fill="x", pady=4)
        self.fuel_preset.set("—")

        sec = SectionFrame(scroll, title="Топливо", glow="orange")
        sec.pack(fill="x", pady=(0, PAD["md"]))
        e = self._fuel_entries
        self._add_entry(sec.body, "Q_i_p", N.Q_n_p, "низшая теплота", "25000", e, "кДж/кг")
        self._add_entry(sec.body, "c_tl", N.c_tl, "теплоёмкость", "1.5", e, "кДж/(кг·К)")
        self._add_entry(sec.body, "t_tl", N.t_tl, "температура", "20", e, "°C")
        self._add_entry(sec.body, "A_p", N.A_p, "зольность", "15", e, "%")
        self._add_entry(sec.body, "W_r_c", N.W_r_c, "влажность", "10", e, "%")
        self._add_entry(sec.body, "CO2_carb", N.CO2_carb, "содержание", "0", e, "%")
        self._add_entry(sec.body, "W1_p", N.W1_p, "влажность до разморозки", "0", e, "%")
        self._add_entry(sec.body, "W2_p", N.W2_p, "безопасная влажность", "0", e, "%")
        self.include_physical = ctk.CTkCheckBox(
            sec.body,
            text=f"Учитывать физическое тепло топлива ({N.i_tl})",
            font=font("label"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=BORDER,
            text_color=TEXT,
        )
        self.include_physical.pack(anchor="w", pady=(PAD["sm"], PAD["xs"]))
        self.fuel_type_var = ctk.StringVar(value="solid")
        type_frame = ctk.CTkFrame(sec.body, fg_color="transparent")
        type_frame.pack(fill="x", pady=PAD["xs"])
        ctk.CTkRadioButton(
            type_frame,
            text="Твёрдое / жидкое",
            variable=self.fuel_type_var,
            value="solid",
            font=font("label"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=BORDER,
            text_color=TEXT,
        ).pack(side="left", padx=(0, PAD["lg"]))
        ctk.CTkRadioButton(
            type_frame,
            text="Газообразное",
            variable=self.fuel_type_var,
            value="gas",
            font=font("label"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=BORDER,
            text_color=TEXT,
        ).pack(side="left")

        sec2 = SectionFrame(scroll, title="Зола и шлак", subtitle=f"Потери {N.q4} и {N.q6}", glow="default")
        sec2.pack(fill="x", pady=(0, PAD["md"]))
        a = self._ash_entries = {}
        self._add_entry(sec2.body, "a_shl", N.a_shl, "доля золы в шлаке", "0.2", a)
        self._add_entry(sec2.body, "a_pl", N.a_pl, "доля золы в отложениях", "0", a)
        self._add_entry(sec2.body, "a_un", N.a_un, "доля золы в уносе", "0.8", a)
        self._add_entry(sec2.body, "C_shl", N.C_shl, "горючее в шлаке", "2", a, "%")
        self._add_entry(sec2.body, "C_pl", N.C_pl, "горючее в отложениях", "0", a, "%")
        self._add_entry(sec2.body, "C_un", N.C_un, "горючее в уносе", "5", a, "%")
        self._add_entry(sec2.body, "t_shl", N.t_shl, "температура шлака", "600", a, "°C")
        self._add_entry(sec2.body, "ct_shl", N.ct_shl, "энтальпия шлака", "0", a, "кДж/кг (0 = из табл.)")

    def _build_flue_tab(self) -> None:
        tab = ctk.CTkFrame(self.main, fg_color="transparent")
        self.tabs["flue"] = tab
        scroll = make_scrollable_tab(tab)
        PageHeader(scroll, "Уходящие газы", f"Расчёт потерь с уходящими газами {N.q2}").pack(
            fill="x", pady=(0, PAD["md"])
        )
        sec = SectionFrame(scroll, title="Параметры газового тракта", glow="cyan")
        sec.pack(fill="x", pady=(0, PAD["md"]))
        f = self._flue_entries = {}
        self._add_entry(sec.body, "I_ukh", N.I_ukh, "энтальпия уходящих газов", "1200", f, "кДж/кг")
        self._add_entry(sec.body, "alpha_ukh", N.alpha_ukh, "избыток воздуха", "1.4", f)
        self._add_entry(sec.body, "I_hv_0", N.I_hv_0, "холодный воздух", "35", f, "кДж/кг")
        self._add_entry(sec.body, "I_gv", N.I_gv, "горячий воздух", "200", f, "кДж/кг")
        self._add_entry(sec.body, "beta", N.beta, "рециркуляция воздуха", "0", f)
        self._add_entry(sec.body, "q3", N.q3, "химическая неполнота", "0.1", f, "%")

    def _build_boiler_tab(self) -> None:
        tab = ctk.CTkFrame(self.main, fg_color="transparent")
        self.tabs["boiler"] = tab
        scroll = make_scrollable_tab(tab)
        PageHeader(scroll, "Параметры котла", "Нагрузка и потери на охлаждение").pack(
            fill="x", pady=(0, PAD["md"])
        )
        sec = SectionFrame(scroll, title="Котёл", glow="orange")
        sec.pack(fill="x", pady=(0, PAD["md"]))
        b = self._boiler_entries = {}
        self._add_entry(sec.body, "D_nom", N.D_nom, "номинальная нагрузка", "100", b, "т/ч")
        self._add_entry(sec.body, "D", N.D, "фактическая нагрузка", "80", b, "т/ч")
        self._add_entry(sec.body, "q5_nom_override", N.q5_nom, "вручную", "0", b, "% (0 = авто)")
        self._add_entry(sec.body, "H_neohl", N.H_neohl, "неохлаждаемые поверхности", "0", b, "м²")
        self._add_entry(sec.body, "Q_v_vn", N.Q_v_vn, "в располагаемом тепле", "0", b, "кДж/кг")

    def _build_useful_tab(self) -> None:
        tab = ctk.CTkFrame(self.main, fg_color="transparent")
        self.tabs["useful"] = tab
        scroll = make_scrollable_tab(tab)
        PageHeader(scroll, "Полезное тепло", f"Расчёт {N.Q_poln} — пар, продувка, отборы").pack(
            fill="x", pady=(0, PAD["md"])
        )
        sec = SectionFrame(scroll, title="Потоки пара и воды", glow="cyan")
        sec.pack(fill="x", pady=(0, PAD["md"]))
        u = self._useful_entries = {}
        self._add_entry(sec.body, "D_pe", N.D_pe, "пар перегретый", "22.2", u, "кг/с", tooltip="22.2 кг/с ≈ 80 т/ч")
        self._add_entry(sec.body, "i_pe", N.i_pe, "энтальпия пара", "3400", u, "кДж/кг")
        self._add_entry(sec.body, "i_pv", N.i_pv, "питательная вода", "420", u, "кДж/кг")
        self._add_entry(sec.body, "D_pr", N.D_pr, "продувка", "0", u, "кг/с")
        self._add_entry(sec.body, "i_sat", N.i_sat, "насыщенная вода в барабане", "1200", u, "кДж/кг")
        self._add_entry(sec.body, "D_pp", N.D_pp, "пар через ПП", "0", u, "кг/с")
        self._add_entry(sec.body, "i_pp_out", N.i_pp_out, "энтальпия на выходе ПП", "0", u, "кДж/кг")
        self._add_entry(sec.body, "i_pp_in", N.i_pp_in, "энтальпия на входе ПП", "0", u, "кДж/кг")
        self._add_entry(sec.body, "Q_otv", N.Q_otv, "отбор тепла", "0", u, "кВт")
        self._add_entry(sec.body, "Q_vod", N.Q_vod, "подогрев воды", "0", u, "кВт")

    def _build_consumption_tab(self) -> None:
        tab = ctk.CTkFrame(self.main, fg_color="transparent")
        self.tabs["consumption"] = tab
        scroll = make_scrollable_tab(tab)
        PageHeader(scroll, "Расход топлива", "Расчётный расход и внешний подогрев воздуха").pack(
            fill="x", pady=(0, PAD["md"])
        )
        sec = SectionFrame(scroll, title="Расход топлива", glow="orange")
        sec.pack(fill="x", pady=(0, PAD["md"]))
        c = self._cons_entries = {}
        self._add_entry(sec.body, "Q_k_override", N.Q_k, "вручную", "0", c, "кВт (0 = из полезного тепла)")

        self.use_ext_air = ctk.CTkCheckBox(
            sec.body,
            text="Подогрев воздуха вне котла",
            font=font("label"),
            fg_color=CYAN,
            hover_color=CYAN_HOVER,
            border_color=BORDER,
            text_color=TEXT,
        )
        self.use_ext_air.pack(anchor="w", pady=(PAD["sm"], PAD["xs"]))
        self._add_entry(sec.body, "beta_prime", N.beta_p, "коэффициент подачи воздуха", "1.2", c)
        self._add_entry(sec.body, "beta_double_prime", N.beta_pp, "коэффициент подачи воздуха", "1.0", c)
        self._add_entry(sec.body, "I_v_vn", N.I_v_vn, "энтальпия подогретого воздуха", "200", c, "кДж/кг")
        self._add_entry(sec.body, "I_v_hv", N.I_v_hv, "энтальпия холодного воздуха", "35", c, "кДж/кг")

        self.use_steam_blast = ctk.CTkCheckBox(
            sec.body,
            text="Паровая обдувка форсунок",
            font=font("label"),
            fg_color=CYAN,
            hover_color=CYAN_HOVER,
            border_color=BORDER,
            text_color=TEXT,
        )
        self.use_steam_blast.pack(anchor="w", pady=(PAD["sm"], PAD["xs"]))
        self._add_entry(sec.body, "G_phi", N.G_phi, "расход пара", "0", c, "кг/кг топлива")
        self._add_entry(sec.body, "i_phi", N.i_phi, "энтальпия пара обдувки", "2800", c, "кДж/кг")

    def _build_results_tab(self) -> None:
        tab = ctk.CTkFrame(self.main, fg_color="transparent")
        self.tabs["results"] = tab
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        from .theme import SCROLLBAR

        scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color="transparent",
            **SCROLLBAR,
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=PAD["lg"], pady=PAD["md"])
        scroll.grid_columnconfigure(0, weight=1)

        top_bar = ctk.CTkFrame(scroll, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, PAD["md"]))

        ctk.CTkLabel(
            top_bar,
            text="Результаты теплового баланса",
            font=font("title"),
            text_color=TEXT,
            anchor="w",
        ).pack(side="left", anchor="n")

        self.back_btn = ctk.CTkButton(
            top_bar,
            text="←  К исходным данным",
            width=200,
            height=34,
            corner_radius=RADIUS["sm"],
            font=font("label"),
            command=self._return_to_calculation,
            **BTN_SECONDARY,
        )
        self.back_btn.pack(side="right", anchor="n")

        metrics = ctk.CTkFrame(scroll, fg_color="transparent")
        metrics.pack(fill="x", pady=(0, PAD["md"]))
        metrics.grid_columnconfigure((0, 1, 2), weight=1)

        self._metric_cards["eta_k"] = MetricCard(
            metrics, f"КПД котла {N.eta_k}", "%", tone="orange"
        )
        self._metric_cards["eta_k"].grid(row=0, column=0, sticky="ew", padx=(0, PAD["sm"]))

        self._metric_cards["Q_poln"] = MetricCard(
            metrics, f"Полезное тепло {N.Q_poln}", "кВт", tone="orange"
        )
        self._metric_cards["Q_poln"].grid(row=0, column=1, sticky="ew", padx=PAD["xs"])

        self._metric_cards["B"] = MetricCard(
            metrics, f"Расход топлива {N.B}", "кг/с", tone="cyan"
        )
        self._metric_cards["B"].grid(row=0, column=2, sticky="ew", padx=(PAD["sm"], 0))

        mid = ctk.CTkFrame(scroll, fg_color="transparent")
        mid.pack(fill="x", pady=(0, PAD["md"]))
        mid.grid_columnconfigure(0, weight=1)
        mid.grid_columnconfigure(1, weight=1)

        details = ctk.CTkFrame(mid, fg_color="transparent")
        details.grid(row=0, column=0, sticky="nsew", padx=(0, PAD["sm"]))
        details.grid_columnconfigure(0, weight=1)

        losses_sec = SectionFrame(details, title="Потери тепла", glow="orange")
        losses_sec.pack(fill="x", pady=(0, PAD["md"]))

        other_sec = SectionFrame(details, title="Баланс и расход", glow="cyan")
        other_sec.pack(fill="x")

        losses_def = [
            ("q2", f"{N.q2} — уходящие газы", "%"),
            ("q3", f"{N.q3} — хим. неполнота", "%"),
            ("q4", f"{N.q4} — мех. неполнота", "%"),
            ("q5", f"{N.q5} — охлаждение", "%"),
            ("q6_shl", f"{N.q6} — тепло шлака", "%"),
            ("q5_oxl", f"{N.q5_oxl} — неохлажд. поверхн.", "%"),
            ("sum_q", f"{N.sum_q} — суммарные потери", "%"),
        ]
        other_def = [
            ("Q_p_p", N.label(N.Q_p_p, "располагаемое тепло"), "кДж/кг"),
            ("phi", N.label(N.phi, "коэфф. сохранения тепла"), "—"),
            ("B_p", N.label(N.B_p, "расчётный расход"), "кг/с"),
        ]

        for key, label, unit in losses_def:
            highlight = key == "sum_q"
            row = ResultRow(losses_sec.body, label, unit, highlight=highlight)
            row.pack(fill="x", pady=2)
            self._result_rows[key] = row

        for key, label, unit in other_def:
            row = ResultRow(other_sec.body, label, unit, tone="cyan")
            row.pack(fill="x", pady=2)
            self._result_rows[key] = row

        chart_col = ctk.CTkFrame(mid, fg_color="transparent")
        chart_col.grid(row=0, column=1, sticky="nsew", padx=(PAD["sm"], 0))
        self._loss_chart = LossChart(chart_col)
        self._loss_chart.pack(fill="both", expand=True)

        self._results_table = DataTable(
            scroll,
            columns=[
                ("param", "Параметр", 280),
                ("value", "Значение", 120),
                ("unit", "Ед.", 80),
                ("group", "Группа", 140),
            ],
            height=200,
        )
        self._results_table.pack(fill="x", pady=(0, PAD["md"]))

        self.warnings_box = InfoBox(scroll, title="Рекомендации по результатам")
        self.warnings_box.pack(fill="x", pady=(0, PAD["md"]))

    def _show_tab(self, key: str) -> None:
        if key in INPUT_TABS:
            self._last_input_tab = key

        self._current_tab = key
        for k, frame in self.tabs.items():
            frame.grid_forget()
            btn = self._section_buttons.get(k)
            if btn:
                btn.set_active(k == key)

        target = self.tabs[key]
        target.grid(row=0, column=0, sticky="nsew")
        self._animate_tab_in(target)

        tab_names = {item[1]: item[0] for item in NAV_SECTIONS}
        self.status_label.configure(text=tab_names.get(key, key))
        if hasattr(self, "_status_dot"):
            color = ACCENT if key == "results" else CYAN
            self._status_dot.configure(text_color=color)

    def _animate_tab_in(self, frame: ctk.CTkFrame) -> None:
        """Лёгкая подсветка перехода: краткий импульс border через after."""
        if self._transition_job:
            try:
                self.after_cancel(self._transition_job)
            except Exception:
                pass
            self._transition_job = None
        try:
            frame.configure(fg_color="#152032")
        except Exception:
            return

        def restore(step: int = 0) -> None:
            colors = ["#152032", "#132029", "#121d27", BG_MAIN]
            if step >= len(colors):
                try:
                    frame.configure(fg_color="transparent")
                except Exception:
                    pass
                return
            try:
                frame.configure(fg_color=colors[step] if step < 3 else "transparent")
            except Exception:
                return
            self._transition_job = self.after(28, lambda: restore(step + 1))

        self._transition_job = self.after(40, lambda: restore(0))

    def _return_to_calculation(self) -> None:
        """Вернуться к последнему разделу ввода данных."""
        self._show_tab(self._last_input_tab)
        self.status_label.configure(text="Измените данные и нажмите «Рассчитать»")

    def _populate_fuel_presets(self) -> None:
        fuels = self.data_provider.list_fuels()
        names = ["—"] + [f["name"] for f in fuels]
        self._fuel_preset_map = {f["name"]: f["id"] for f in fuels}
        self.fuel_preset.configure(values=names)
        self.fuel_preset.set("—")

    def _on_fuel_preset(self, choice: str) -> None:
        if choice == "—":
            self._current_fuel_preset_id = None
            return
        fuel_id = self._fuel_preset_map.get(choice)
        if not fuel_id:
            return
        self._current_fuel_preset_id = fuel_id
        props = self.data_provider.get_fuel_properties(fuel_id)
        if not props:
            return
        mapping = {
            "Q_i_p": props.get("Q_i_p"),
            "A_p": props.get("A_p"),
            "W_r_c": props.get("W_r_c"),
            "c_tl": props.get("c_tl"),
            "CO2_carb": props.get("CO2_carb"),
        }
        for key, val in mapping.items():
            if val is not None and key in self._fuel_entries:
                self._fuel_entries[key].set_value(val)
        if props.get("fuel_type") == "gaseous":
            self.fuel_type_var.set("gas")
        else:
            self.fuel_type_var.set("solid")
        self.status_label.configure(text=f"Топливо: {choice}")

    def _set_fuel_preset_by_id(self, fuel_id: str | None) -> None:
        """Восстановить выбор в справочнике топлива по id."""
        self._current_fuel_preset_id = fuel_id
        if not fuel_id:
            self.fuel_preset.set("—")
            return
        for name, fid in self._fuel_preset_map.items():
            if fid == fuel_id:
                self.fuel_preset.set(name)
                return
        self.fuel_preset.set("—")

    def _collect_input(self) -> HeatBalanceInput:
        fe = self._fuel_entries
        ae = self._ash_entries
        fl = self._flue_entries
        bo = self._boiler_entries
        us = self._useful_entries
        co = self._cons_entries

        q5_override = bo["q5_nom_override"].get_float()
        Q_k = co["Q_k_override"].get_float()

        return HeatBalanceInput(
            fuel=FuelProperties(
                fuel_type=FuelType.GASEOUS if self.fuel_type_var.get() == "gas" else FuelType.SOLID_LIQUID,
                Q_i_p=fe["Q_i_p"].get_float(25000),
                c_tl=fe["c_tl"].get_float(1.5),
                t_tl=fe["t_tl"].get_float(20),
                include_physical_heat=bool(self.include_physical.get()),
                W1_p=fe["W1_p"].get_float(),
                W2_p=fe["W2_p"].get_float(),
                CO2_carb=fe["CO2_carb"].get_float(),
                A_p=fe["A_p"].get_float(15),
                W_r_c=fe["W_r_c"].get_float(10),
            ),
            ash=AshLosses(
                a_shl=ae["a_shl"].get_float(0.2),
                a_pl=ae["a_pl"].get_float(),
                a_un=ae["a_un"].get_float(0.8),
                C_shl=ae["C_shl"].get_float(2),
                C_pl=ae["C_pl"].get_float(),
                C_un=ae["C_un"].get_float(5),
                t_shl=ae["t_shl"].get_float(600),
                ct_shl=ae["ct_shl"].get_float(),
            ),
            flue=FlueGasParams(
                I_ukh=fl["I_ukh"].get_float(1200),
                alpha_ukh=fl["alpha_ukh"].get_float(1.4),
                I_hv_0=fl["I_hv_0"].get_float(35),
                I_gv=fl["I_gv"].get_float(200),
                beta=fl["beta"].get_float(),
                q3=fl["q3"].get_float(0.1),
            ),
            boiler=BoilerParams(
                D_nom=bo["D_nom"].get_float(100),
                D=bo["D"].get_float(80),
                q5_nom_override=q5_override if q5_override > 0 else None,
                H_neohl=bo["H_neohl"].get_float(),
                Q_v_vn=bo["Q_v_vn"].get_float(),
            ),
            useful=UsefulHeatParams(
                D_pe=us["D_pe"].get_float(22.2),
                i_pe=us["i_pe"].get_float(3400),
                i_pv=us["i_pv"].get_float(420),
                D_pr=us["D_pr"].get_float(),
                i_sat=us["i_sat"].get_float(1200),
                D_pp=us["D_pp"].get_float(),
                i_pp_out=us["i_pp_out"].get_float(),
                i_pp_in=us["i_pp_in"].get_float(),
                Q_otv=us["Q_otv"].get_float(),
                Q_vod=us["Q_vod"].get_float(),
            ),
            consumption=FuelConsumptionParams(
                Q_k_override=Q_k if Q_k > 0 else None,
                use_external_air_heat=bool(self.use_ext_air.get()),
                beta_prime=co["beta_prime"].get_float(1.2),
                beta_double_prime=co["beta_double_prime"].get_float(1.0),
                I_v_vn=co["I_v_vn"].get_float(200),
                I_v_hv=co["I_v_hv"].get_float(35),
                use_steam_blast=bool(self.use_steam_blast.get()),
                G_phi=co["G_phi"].get_float(),
                i_phi=co["i_phi"].get_float(2800),
            ),
        )

    def _on_calculate(self) -> None:
        if self._current_tab in INPUT_TABS:
            self._last_input_tab = self._current_tab

        try:
            inp = self._collect_input()
            result = self.calculator.calculate(inp)
            self._last_result = result
            self._display_results(result)
            self.status_label.configure(text="Расчёт выполнен успешно")
            self._show_tab("results")
        except Exception as exc:
            messagebox.showerror("Ошибка расчёта", str(exc))
            self.status_label.configure(text="Ошибка при расчёте")

    def _display_results(self, r: HeatBalanceResult) -> None:
        fmt = {
            "Q_p_p": f"{r.Q_p_p:.1f}",
            "q2": f"{r.q2:.3f}",
            "q3": f"{r.q3:.3f}",
            "q4": f"{r.q4:.3f}",
            "q5": f"{r.q5:.3f}",
            "q6_shl": f"{r.q6_shl:.3f}",
            "q5_oxl": f"{r.q5_oxl:.3f}",
            "sum_q": f"{r.sum_q:.3f}",
            "eta_k": f"{r.eta_k:.2f}",
            "phi": f"{r.phi:.4f}",
            "Q_poln": f"{r.Q_poln:.0f}",
            "B": f"{r.B:.3f}",
            "B_p": f"{r.B_p:.4f}",
        }
        for key, val in fmt.items():
            if key in self._result_rows:
                self._result_rows[key].set(val)

        if "eta_k" in self._metric_cards:
            self._metric_cards["eta_k"].set(fmt["eta_k"])
        if "Q_poln" in self._metric_cards:
            self._metric_cards["Q_poln"].set(fmt["Q_poln"])
        if "B" in self._metric_cards:
            self._metric_cards["B"].set(fmt["B"])

        if self._loss_chart is not None:
            self._loss_chart.plot(
                [
                    f"{N.q2} ух.г.",
                    f"{N.q3} хим.",
                    f"{N.q4} мех.",
                    f"{N.q5} охл.",
                    f"{N.q6} шлак",
                    f"{N.q5_oxl} неохл.",
                ],
                [r.q2, r.q3, r.q4, r.q5, r.q6_shl, r.q5_oxl],
            )

        if self._results_table is not None:
            table_rows = [
                {"param": f"{N.eta_k} — КПД котла", "value": fmt["eta_k"], "unit": "%", "group": "Ключевые"},
                {"param": f"{N.Q_poln} — полезное тепло", "value": fmt["Q_poln"], "unit": "кВт", "group": "Ключевые"},
                {"param": f"{N.B} — расход топлива", "value": fmt["B"], "unit": "кг/с", "group": "Ключевые"},
                {"param": f"{N.q2} — уходящие газы", "value": fmt["q2"], "unit": "%", "group": "Потери"},
                {"param": f"{N.q3} — хим. неполнота", "value": fmt["q3"], "unit": "%", "group": "Потери"},
                {"param": f"{N.q4} — мех. неполнота", "value": fmt["q4"], "unit": "%", "group": "Потери"},
                {"param": f"{N.q5} — охлаждение", "value": fmt["q5"], "unit": "%", "group": "Потери"},
                {"param": f"{N.q6} — тепло шлака", "value": fmt["q6_shl"], "unit": "%", "group": "Потери"},
                {"param": f"{N.q5_oxl} — неохлажд. поверхн.", "value": fmt["q5_oxl"], "unit": "%", "group": "Потери"},
                {"param": f"{N.sum_q} — суммарные потери", "value": fmt["sum_q"], "unit": "%", "group": "Потери"},
                {"param": f"{N.Q_p_p} — располагаемое тепло", "value": fmt["Q_p_p"], "unit": "кДж/кг", "group": "Баланс"},
                {"param": f"{N.phi} — коэфф. сохранения", "value": fmt["phi"], "unit": "—", "group": "Баланс"},
                {"param": f"{N.B_p} — расчётный расход", "value": fmt["B_p"], "unit": "кг/с", "group": "Баланс"},
            ]
            self._results_table.set_rows(table_rows)

        if r.warnings:
            self.warnings_box.set_text("\n\n".join(f"• {w}" for w in r.warnings))
        else:
            self.warnings_box.set_text("Дополнительных рекомендаций нет.")

    def _save_json(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        data: dict[str, Any] = {
            "version": 2,
            "fuel_preset_id": self._current_fuel_preset_id,
            "input": self._dataclass_to_dict(self._collect_input()),
        }
        if self._last_result:
            data["result"] = self._last_result.to_dict()
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status_label.configure(text=f"Сохранено: {Path(path).name}")

    def _load_json(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        inp = data.get("input", {})
        self._apply_input_dict(inp)
        fuel_preset_id = data.get("fuel_preset_id")
        if fuel_preset_id:
            self._set_fuel_preset_by_id(fuel_preset_id)
        else:
            self._set_fuel_preset_by_id(None)
        self.status_label.configure(text=f"Загружено: {Path(path).name}")

    def _apply_input_dict(self, inp: dict[str, Any]) -> None:
        fuel = inp.get("fuel", {})
        for key, entry in self._fuel_entries.items():
            if key in fuel:
                entry.set_value(fuel[key])
        if fuel.get("include_physical_heat"):
            self.include_physical.select()
        else:
            self.include_physical.deselect()
        ft = fuel.get("fuel_type", "")
        self.fuel_type_var.set("gas" if "gaseous" in str(ft) else "solid")

        for section_key, entries in [
            ("ash", self._ash_entries),
            ("flue", self._flue_entries),
            ("boiler", self._boiler_entries),
            ("useful", self._useful_entries),
            ("consumption", self._cons_entries),
        ]:
            section = inp.get(section_key, {})
            for key, entry in entries.items():
                if key in section:
                    entry.set_value(section[key])

        cons = inp.get("consumption", {})
        if cons.get("use_external_air_heat"):
            self.use_ext_air.select()
        else:
            self.use_ext_air.deselect()
        if cons.get("use_steam_blast"):
            self.use_steam_blast.select()
        else:
            self.use_steam_blast.deselect()

    @staticmethod
    def _dataclass_to_dict(obj: Any) -> dict[str, Any]:
        from dataclasses import asdict, is_dataclass

        if is_dataclass(obj):
            return asdict(obj)
        return {}

    def activate_plugin(self, plugin_id: str) -> None:
        plugin = self.plugin_registry.get(plugin_id)
        if plugin and hasattr(plugin, "open_window"):
            plugin.open_window(self)

    def get_steam_form_values(self) -> dict[str, float]:
        """Текущие энтальпии из формы — для обратного расчёта в калькуляторе пара."""
        us = self._useful_entries
        co = self._cons_entries
        return {
            "i_pe": us["i_pe"].get_float(3400),
            "i_pv": us["i_pv"].get_float(420),
            "i_sat": us["i_sat"].get_float(1200),
            "i_phi": co["i_phi"].get_float(2800),
        }

    def apply_steam_values(self, values: dict[str, float]) -> None:
        """Подставить энтальпии из калькулятора свойств пара в форму расчёта."""
        useful_keys = set(self._useful_entries.keys())
        cons_keys = set(self._cons_entries.keys())
        applied: list[str] = []
        touched_tabs: list[str] = []

        for key, val in values.items():
            text = f"{val:.2f}"
            if key in useful_keys:
                entry = self._useful_entries[key]
                entry.set_value(text)
                entry.mark_changed(hold_ms=15000)
                applied.append(key)
                if "useful" not in touched_tabs:
                    touched_tabs.append("useful")
            elif key in cons_keys:
                entry = self._cons_entries[key]
                entry.set_value(text)
                entry.mark_changed(hold_ms=15000)
                applied.append(key)
                if "consumption" not in touched_tabs:
                    touched_tabs.append("consumption")

        if applied:
            # Один переход: к первому затронутому разделу, без перебора всех шагов
            self._show_tab(touched_tabs[0])
            names = ", ".join(applied)
            tab_names = {item[1]: item[0] for item in NAV_SECTIONS}
            tabs_hint = " → ".join(tab_names.get(t, t) for t in touched_tabs)
            self.status_label.configure(
                text=f"Подставлено: {names}. Поля подсвечены ~15 с. Разделы: {tabs_hint}"
            )

    def highlight_steam_source_fields(self, keys: list[str] | None = None) -> None:
        """
        Подсветить поля-источники для «Энтальпии из баланса».
        Без перелистывания шагов — пометки видны при ручном переходе.
        """
        keys = keys or ["i_pe", "i_pv", "i_sat", "i_phi"]
        marked: list[str] = []
        for key in keys:
            if key in self._useful_entries:
                self._useful_entries[key].mark_changed(hold_ms=15000)
                marked.append(key)
            elif key in self._cons_entries:
                self._cons_entries[key].mark_changed(hold_ms=15000)
                marked.append(key)
        # Не вызываем _show_tab в цикле — иначе быстро мелькают разделы
        if marked:
            names = ", ".join(marked)
            self.status_label.configure(
                text=f"Источник для калькулятора пара: {names} (поля подсвечены ~15 с на шагах «Полезное тепло» / «Расход топлива»)"
            )
