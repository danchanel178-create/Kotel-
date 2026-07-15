"""
Плагин: калькулятор свойств воды и пара по IAPWS-IF97.

Функционал аналогичен WaterSteamPro Calculator: режимы ввода (P,T)/(P,x)/(P,h)…,
полный вывод термодинамических и транспортных свойств, таблица насыщения,
мастер расчёта точек котла, подстановка энтальпий в тепловой баланс.
"""

from __future__ import annotations

from typing import Any

try:
    import customtkinter as ctk
except ImportError:
    ctk = None  # type: ignore

from src.core.steam import (
    IAPWS_AVAILABLE,
    BoilerCycleResult,
    InputMode,
    PressureUnit,
    SaturationInput,
    SaturationProperties,
    SteamCalculationError,
    SteamProperties,
    TableAxis,
    TemperatureUnit,
    calculate_boiler_cycle,
    calculate_from_enthalpy,
    calculate_state,
    default_inputs,
    find_wsp_executable,
    format_iapws_error,
    generate_saturation_table,
    input_kinds,
    input_labels,
    input_units,
    launch_wsp,
    parse_float,
    pressure_to_mpa,
    saturation_by_pressure,
    saturation_by_temperature,
    saturation_table_as_text,
    temperature_to_c,
)
from src.plugins.base import UtilityPlugin
from src.ui import notation as N
from src.ui.theme import (
    ACCENT,
    ACCENT_HOVER,
    BG_CARD,
    BG_CARD_SOFT,
    BG_INPUT,
    BG_MAIN,
    BORDER,
    BTN_APPLY,
    BTN_SECONDARY,
    ERROR,
    OPTION_MENU,
    PAD,
    RADIUS,
    SCROLLBAR,
    SUCCESS,
    TABVIEW,
    TEXT,
    TEXT_MUTED,
    font,
)

# Стартовый и минимальный размер — две колонки (ввод ~340 + результаты ~360) + поля
WIN_W = 1100
WIN_H = 800
MIN_W = 960
MIN_H = 700
PANE_LEFT_MIN = 340
PANE_RIGHT_MIN = 360


class SteamQualityPlugin(UtilityPlugin):
    id = "steam_quality"
    name = "Свойства пара"
    version = "3.1.0"
    description = "Калькулятор свойств воды и пара IAPWS-IF97"

    def activate(self, host: Any) -> None:
        pass

    def open_window(self, parent: Any) -> None:
        if ctk is None:
            return
        SteamCalculatorWindow(parent, host=parent)


class SteamCalculatorWindow:
    """Окно калькулятора свойств воды/пара."""

    def __init__(self, parent: Any, host: Any) -> None:
        self._host = host
        self._last_state: SteamProperties | None = None
        self._last_sat: SaturationProperties | None = None
        self._last_boiler: BoilerCycleResult | None = None
        self._last_table_text = ""
        self._history: list[str] = []
        self._state_result_rows: list[tuple[str, str, str]] = []

        self.win = ctk.CTkToplevel(parent)
        self.win.title("Свойства воды и пара — IAPWS-IF97")
        self.win.resizable(True, True)
        self.win.configure(fg_color=BG_MAIN)
        self.win.transient(parent)
        self._apply_initial_geometry(parent)
        self.win.after(50, self._enable_native_caption_buttons)

        self._build_header()
        self._build_tabs()

    def _apply_initial_geometry(self, parent: Any) -> None:
        """Задать стартовый размер не меньше минимума и уместить окно на экране."""
        screen_w = int(self.win.winfo_screenwidth())
        screen_h = int(self.win.winfo_screenheight())
        # Запас под панель задач и рамку; не больше самого экрана
        max_w = max(640, screen_w - 48)
        max_h = max(480, screen_h - 72)
        w = min(max(WIN_W, MIN_W), max_w)
        h = min(max(WIN_H, MIN_H), max_h)
        self.win.minsize(min(MIN_W, w), min(MIN_H, h))

        try:
            parent.update_idletasks()
            px = int(parent.winfo_rootx())
            py = int(parent.winfo_rooty())
            pw = int(parent.winfo_width())
            ph = int(parent.winfo_height())
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
        except Exception:
            x = max(0, (screen_w - w) // 2)
            y = max(0, (screen_h - h) // 2)

        x = max(0, min(x, max(0, screen_w - w)))
        y = max(0, min(y, max(0, screen_h - h)))
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def _enable_native_caption_buttons(self) -> None:
        """Включить в заголовке Windows кнопки свернуть / развернуть / закрыть."""
        import sys

        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes

            user32 = ctypes.windll.user32
            GWL_STYLE = -16
            WS_MINIMIZEBOX = 0x00020000
            WS_MAXIMIZEBOX = 0x00010000
            WS_SYSMENU = 0x00080000
            WS_THICKFRAME = 0x00040000
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020

            hwnd = user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            style |= WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU | WS_THICKFRAME
            user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
        except Exception:
            pass

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.win, fg_color=BG_CARD_SOFT, corner_radius=0)
        header.pack(fill="x")

        top = ctk.CTkFrame(header, fg_color="transparent")
        top.pack(fill="x", padx=PAD["lg"], pady=(PAD["md"], PAD["xs"]))

        ctk.CTkLabel(
            top,
            text="Калькулятор свойств воды и пара",
            font=font("section"),
            text_color=TEXT,
        ).pack(side="left")

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(side="right")
        if find_wsp_executable():
            ctk.CTkButton(
                btn_frame,
                text="Открыть WSP",
                width=120,
                height=30,
                font=font("small"),
                command=self._open_wsp,
                **BTN_SECONDARY,
            ).pack(side="left", padx=(0, PAD["xs"]))
        ctk.CTkButton(
            btn_frame,
            text="Энтальпии из баланса",
            width=170,
            height=30,
            font=font("small"),
            command=self._load_from_balance,
            **BTN_SECONDARY,
        ).pack(side="left")
        # Краткая подсказка под кнопками шапки
        hint = (
            "«Энтальпии из баланса» — взять i_пе, i_пв, i_нас, i_φ из формы расчёта и показать их свойства здесь"
            if IAPWS_AVAILABLE
            else "⚠ iapws не установлен — pip install iapws"
        )
        ctk.CTkLabel(
            header,
            text=hint,
            font=font("small"),
            text_color=TEXT_MUTED if IAPWS_AVAILABLE else ERROR,
            anchor="w",
        ).pack(anchor="w", padx=PAD["lg"], pady=(PAD["xs"], PAD["md"]))

    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(self.win, **TABVIEW)
        self.tabs.pack(fill="both", expand=True, padx=PAD["lg"], pady=(0, PAD["md"]))

        for name in ("Состояние", "Котёл", "Насыщение", "Таблица"):
            self.tabs.add(name)

        self._build_state_tab(self.tabs.tab("Состояние"))
        self._build_boiler_tab(self.tabs.tab("Котёл"))
        self._build_saturation_tab(self.tabs.tab("Насыщение"))
        self._build_table_tab(self.tabs.tab("Таблица"))

    # ── Вкладка «Состояние» ─────────────────────────────────────────────

    def _build_state_tab(self, tab: ctk.CTkFrame) -> None:
        left, right = self._split_panes(tab)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(left, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(body, text="Входные данные", font=font("label"), text_color=TEXT).pack(
            anchor="w", padx=PAD["md"], pady=(PAD["md"], PAD["sm"])
        )

        mode_row = ctk.CTkFrame(body, fg_color="transparent")
        mode_row.pack(fill="x", padx=PAD["md"], pady=PAD["xs"])
        self._mode_var = ctk.StringVar(value=InputMode.PT.value)
        self._option_menu(
            mode_row,
            variable=self._mode_var,
            values=[m.value for m in InputMode],
            command=self._on_mode_change,
            font=font("label"),
            width=280,
        ).pack(anchor="w")

        self._p_unit_var = ctk.StringVar(value=PressureUnit.MPA.value)
        self._t_unit_var = ctk.StringVar(value=TemperatureUnit.C.value)

        self._inputs_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._inputs_frame.pack(fill="x", padx=PAD["md"], pady=PAD["sm"])
        self._in1_var = ctk.StringVar()
        self._in2_var = ctk.StringVar()
        self._in1_label = ctk.CTkLabel(self._inputs_frame, text="", font=font("label"), text_color=TEXT)
        self._in2_label = ctk.CTkLabel(self._inputs_frame, text="", font=font("label"), text_color=TEXT)

        self._in1_row = ctk.CTkFrame(self._inputs_frame, fg_color="transparent")
        self._in2_row = ctk.CTkFrame(self._inputs_frame, fg_color="transparent")
        self._in1_entry = ctk.CTkEntry(
            self._in1_row, textvariable=self._in1_var, width=160, height=34,
            font=font("label"), fg_color=BG_INPUT, border_color=BORDER, text_color=TEXT,
        )
        self._in2_entry = ctk.CTkEntry(
            self._in2_row, textvariable=self._in2_var, width=160, height=34,
            font=font("label"), fg_color=BG_INPUT, border_color=BORDER, text_color=TEXT,
        )
        self._in1_unit = ctk.CTkLabel(self._in1_row, text="", font=font("small"), text_color=TEXT_MUTED)
        self._in2_unit = ctk.CTkLabel(self._in2_row, text="", font=font("small"), text_color=TEXT_MUTED)
        self._p_unit_menu = self._option_menu(
            self._in1_row,
            variable=self._p_unit_var,
            values=[u.value for u in PressureUnit],
            command=self._on_unit_change,
            font=font("small"),
            width=130,
        )
        self._t_unit_menu = self._option_menu(
            self._in1_row,
            variable=self._t_unit_var,
            values=[u.value for u in TemperatureUnit],
            command=self._on_unit_change,
            font=font("small"),
            width=80,
        )
        self._p_unit_menu_2 = self._option_menu(
            self._in2_row,
            variable=self._p_unit_var,
            values=[u.value for u in PressureUnit],
            command=self._on_unit_change,
            font=font("small"),
            width=130,
        )
        self._t_unit_menu_2 = self._option_menu(
            self._in2_row,
            variable=self._t_unit_var,
            values=[u.value for u in TemperatureUnit],
            command=self._on_unit_change,
            font=font("small"),
            width=80,
        )

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD["md"], pady=(PAD["sm"], PAD["xs"]))
        ctk.CTkButton(
            btn_row, text="Рассчитать", width=130, height=36,
            font=font("label"), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._calc_state,
        ).pack(side="left", padx=(0, PAD["sm"]))
        ctk.CTkButton(btn_row, text="Очистить", width=90, height=36, font=font("label"), command=self._clear_state, **BTN_SECONDARY).pack(side="left")
        ctk.CTkButton(btn_row, text="Копировать", width=110, height=36, font=font("label"), command=self._copy_state, **BTN_SECONDARY).pack(side="left", padx=(PAD["sm"], 0))

        self._state_error = ctk.CTkLabel(body, text="", font=font("small"), text_color=ERROR, wraplength=300)
        self._state_error.pack(anchor="w", padx=PAD["md"], pady=(0, PAD["sm"]))

        # Блок подстановки — у нижнего края левой колонки
        apply_wrap = ctk.CTkFrame(left, fg_color="transparent")
        apply_wrap.grid(row=1, column=0, sticky="swe")
        self._apply_block(apply_wrap, [
            (f"→ {N.i_pe}", "i_pe"),
            (f"→ {N.i_pv}", "i_pv"),
            (f"→ {N.i_sat}", "i_sat"),
            (f"→ {N.i_phi}", "i_phi"),
        ], self._apply_enthalpy)

        ctk.CTkLabel(right, text="Результаты расчёта", font=font("label"), text_color=TEXT).grid(
            row=0, column=0, sticky="w", padx=PAD["md"], pady=(PAD["md"], PAD["sm"])
        )
        self._state_scroll = self._results_scroll(right)
        self._state_scroll.grid(row=1, column=0, sticky="nsew", padx=(PAD["sm"], PAD["sm"]), pady=(0, PAD["sm"]))

        self._on_mode_change(self._mode_var.get())
        self._in1_entry.bind("<Return>", lambda _e: self._calc_state())
        self._in2_entry.bind("<Return>", lambda _e: self._calc_state())

    # ── Вкладка «Котёл» ─────────────────────────────────────────────────

    def _build_boiler_tab(self, tab: ctk.CTkFrame) -> None:
        left, right = self._split_panes(tab)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(left, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(body, text="Точки цикла котла", font=font("label"), text_color=TEXT).pack(
            anchor="w", padx=PAD["md"], pady=(PAD["md"], PAD["sm"])
        )

        form = ctk.CTkFrame(body, fg_color="transparent")
        form.pack(fill="x", padx=PAD["md"])

        self._boiler_p_var = ctk.StringVar(value="4.0")
        self._boiler_t_fw_var = ctk.StringVar(value="150")
        self._boiler_t_sh_var = ctk.StringVar(value="500")
        self._boiler_x_var = ctk.StringVar(value="")
        self._boiler_wet_var = ctk.BooleanVar(value=False)

        self._field_with_unit(form, "Давление барабана", self._boiler_p_var, kind="pressure")
        self._field_with_unit(form, "T питательной воды", self._boiler_t_fw_var, kind="temperature")

        wet_row = ctk.CTkFrame(form, fg_color="transparent")
        wet_row.pack(fill="x", pady=(PAD["sm"], 0))
        ctk.CTkCheckBox(
            wet_row,
            text="Влажный пар (задать x вместо T)",
            variable=self._boiler_wet_var,
            font=font("label"),
            command=self._toggle_boiler_steam_mode,
        ).pack(anchor="w")

        self._boiler_t_sh_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._boiler_t_sh_frame.pack(fill="x")
        self._field_with_unit(self._boiler_t_sh_frame, "T перегретого пара", self._boiler_t_sh_var, kind="temperature")

        self._boiler_x_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._field(self._boiler_x_frame, "Качество пара x", "0…1", self._boiler_x_var)

        self._toggle_boiler_steam_mode()

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD["md"], pady=PAD["md"])
        ctk.CTkButton(
            btn_row, text="Рассчитать котёл", width=160, height=36,
            font=font("label"), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._calc_boiler,
        ).pack(side="left")

        self._boiler_error = ctk.CTkLabel(body, text="", font=font("small"), text_color=ERROR, wraplength=300)
        self._boiler_error.pack(anchor="w", padx=PAD["md"], pady=(0, PAD["md"]))

        apply_wrap = ctk.CTkFrame(left, fg_color="transparent")
        apply_wrap.grid(row=1, column=0, sticky="swe")
        frame = ctk.CTkFrame(apply_wrap, fg_color=BG_CARD_SOFT, corner_radius=RADIUS["sm"])
        frame.pack(fill="x", padx=PAD["md"], pady=(0, PAD["md"]))
        ctk.CTkLabel(frame, text="Подставить в тепловой баланс", font=font("small"), text_color=TEXT_MUTED).pack(
            anchor="w", padx=PAD["sm"], pady=(PAD["sm"], PAD["xs"])
        )
        ctk.CTkButton(
            frame, text="Подставить всё", width=160, height=32,
            font=font("small"), command=self._apply_boiler_all, **BTN_APPLY,
        ).pack(anchor="w", padx=PAD["sm"], pady=(0, PAD["sm"]))

        ctk.CTkLabel(right, text="Энтальпии и перегрев", font=font("label"), text_color=TEXT).grid(
            row=0, column=0, sticky="w", padx=PAD["md"], pady=(PAD["md"], PAD["sm"])
        )
        self._boiler_scroll = self._results_scroll(right)
        self._boiler_scroll.grid(row=1, column=0, sticky="nsew", padx=(PAD["sm"], PAD["sm"]), pady=(0, PAD["sm"]))

    # ── Вкладка «Насыщение» ─────────────────────────────────────────────

    def _build_saturation_tab(self, tab: ctk.CTkFrame) -> None:
        left, right = self._split_panes(tab)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(left, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(body, text="Линия насыщения", font=font("label"), text_color=TEXT).pack(
            anchor="w", padx=PAD["md"], pady=(PAD["md"], PAD["sm"])
        )

        self._sat_mode_var = ctk.StringVar(value=SaturationInput.BY_PRESSURE.value)
        sat_mode_row = ctk.CTkFrame(body, fg_color="transparent")
        sat_mode_row.pack(fill="x", padx=PAD["md"], pady=PAD["xs"])
        ctk.CTkRadioButton(
            sat_mode_row, text="По давлению", variable=self._sat_mode_var,
            value=SaturationInput.BY_PRESSURE.value, font=font("label"),
            command=self._on_sat_mode_change,
        ).pack(anchor="w")
        ctk.CTkRadioButton(
            sat_mode_row, text="По температуре", variable=self._sat_mode_var,
            value=SaturationInput.BY_TEMPERATURE.value, font=font("label"),
            command=self._on_sat_mode_change,
        ).pack(anchor="w", pady=(PAD["xs"], 0))

        self._sat_input_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._sat_input_frame.pack(fill="x", padx=PAD["md"], pady=PAD["sm"])
        self._sat_label = ctk.CTkLabel(self._sat_input_frame, text="Давление", font=font("label"), text_color=TEXT)
        self._sat_label.pack(anchor="w")
        self._sat_var = ctk.StringVar(value="4.0")
        sat_row = ctk.CTkFrame(self._sat_input_frame, fg_color="transparent")
        sat_row.pack(fill="x", pady=(PAD["xs"], 0))
        self._sat_entry = ctk.CTkEntry(
            sat_row, textvariable=self._sat_var, width=160, height=34,
            font=font("label"), fg_color=BG_INPUT, border_color=BORDER, text_color=TEXT,
        )
        self._sat_entry.pack(side="left")
        self._sat_unit_menu = self._option_menu(
            sat_row,
            variable=self._p_unit_var,
            values=[u.value for u in PressureUnit],
            command=lambda _c: self._on_sat_mode_change(),
            font=font("small"),
            width=130,
        )
        self._sat_t_unit_menu = self._option_menu(
            sat_row,
            variable=self._t_unit_var,
            values=[u.value for u in TemperatureUnit],
            command=lambda _c: self._on_sat_mode_change(),
            font=font("small"),
            width=80,
        )
        self._sat_unit_label = ctk.CTkLabel(sat_row, text="", font=font("small"), text_color=TEXT_MUTED)
        self._sat_unit_menu.pack(side="left", padx=(PAD["sm"], 0))

        ctk.CTkButton(
            body, text="Рассчитать насыщение", width=200, height=36,
            font=font("label"), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._calc_saturation,
        ).pack(anchor="w", padx=PAD["md"], pady=PAD["sm"])

        self._sat_error = ctk.CTkLabel(body, text="", font=font("small"), text_color=ERROR, wraplength=300)
        self._sat_error.pack(anchor="w", padx=PAD["md"])

        apply_wrap = ctk.CTkFrame(left, fg_color="transparent")
        apply_wrap.grid(row=1, column=0, sticky="swe")
        self._apply_block(apply_wrap, [
            (f"→ {N.i_sat} ({N.h_l})", "i_sat_l"),
            (f"→ {N.i_pe} ({N.h_v})", "i_pe_v"),
        ], self._apply_sat_button)

        ctk.CTkLabel(right, text="Свойства на линии насыщения", font=font("label"), text_color=TEXT).grid(
            row=0, column=0, sticky="w", padx=PAD["md"], pady=(PAD["md"], PAD["sm"])
        )
        self._sat_scroll = self._results_scroll(right)
        self._sat_scroll.grid(row=1, column=0, sticky="nsew", padx=(PAD["sm"], PAD["sm"]), pady=(0, PAD["sm"]))

        self._on_sat_mode_change()
        self._sat_entry.bind("<Return>", lambda _e: self._calc_saturation())

    # ── Вкладка «Таблица» ───────────────────────────────────────────────

    def _build_table_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        ctrl = self._card(tab)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, PAD["sm"]))
        ctrl_inner = ctk.CTkFrame(ctrl, fg_color="transparent")
        ctrl_inner.pack(fill="x", padx=PAD["md"], pady=PAD["md"])

        ctk.CTkLabel(ctrl_inner, text="Таблица насыщения (IAPWS-IF97)", font=font("label"), text_color=TEXT).grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, PAD["sm"])
        )

        self._tbl_axis_var = ctk.StringVar(value="По давлению")
        self._tbl_axis_map = {
            "По давлению": TableAxis.BY_PRESSURE.value,
            "По температуре": TableAxis.BY_TEMPERATURE.value,
        }
        ctk.CTkLabel(ctrl_inner, text="Ось", font=font("small"), text_color=TEXT_MUTED).grid(row=1, column=0, sticky="w")
        self._option_menu(
            ctrl_inner,
            variable=self._tbl_axis_var,
            values=list(self._tbl_axis_map.keys()),
            command=self._on_table_axis_change,
            width=160,
            font=font("label"),
        ).grid(row=2, column=0, sticky="w", padx=(0, PAD["md"]))

        self._tbl_start_label = ctk.CTkLabel(ctrl_inner, text="От", font=font("small"), text_color=TEXT_MUTED)
        self._tbl_start_label.grid(row=1, column=1, sticky="w")
        self._tbl_start_var = ctk.StringVar(value="0.1")
        ctk.CTkEntry(
            ctrl_inner,
            textvariable=self._tbl_start_var,
            width=90,
            fg_color=BG_INPUT,
            border_color=BORDER,
            text_color=TEXT,
        ).grid(row=2, column=1, sticky="w", padx=(0, PAD["md"]))

        self._tbl_end_label = ctk.CTkLabel(ctrl_inner, text="До", font=font("small"), text_color=TEXT_MUTED)
        self._tbl_end_label.grid(row=1, column=2, sticky="w")
        self._tbl_end_var = ctk.StringVar(value="10")
        ctk.CTkEntry(
            ctrl_inner,
            textvariable=self._tbl_end_var,
            width=90,
            fg_color=BG_INPUT,
            border_color=BORDER,
            text_color=TEXT,
        ).grid(row=2, column=2, sticky="w", padx=(0, PAD["md"]))

        ctk.CTkLabel(ctrl_inner, text="Точек", font=font("small"), text_color=TEXT_MUTED).grid(row=1, column=3, sticky="w")
        self._tbl_n_var = ctk.StringVar(value="15")
        ctk.CTkEntry(
            ctrl_inner,
            textvariable=self._tbl_n_var,
            width=60,
            fg_color=BG_INPUT,
            border_color=BORDER,
            text_color=TEXT,
        ).grid(row=2, column=3, sticky="w", padx=(0, PAD["md"]))

        ctk.CTkButton(
            ctrl_inner, text="Построить", width=110, height=32,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._calc_table,
        ).grid(row=2, column=4, padx=(0, PAD["sm"]))
        ctk.CTkButton(
            ctrl_inner, text="Копировать", width=110, height=32,
            command=self._copy_table, **BTN_SECONDARY,
        ).grid(row=2, column=5)

        # Баннер ошибки — отдельная строка под панелью, с переносом текста
        self._tbl_error_frame = ctk.CTkFrame(
            tab,
            fg_color="#3f1d1d",
            border_width=1,
            border_color=ERROR,
            corner_radius=RADIUS["sm"],
        )
        self._tbl_error_inner = ctk.CTkFrame(self._tbl_error_frame, fg_color="transparent")
        self._tbl_error_inner.pack(fill="x", padx=PAD["md"], pady=PAD["sm"])
        ctk.CTkLabel(
            self._tbl_error_inner,
            text="Ошибка",
            font=font("small"),
            text_color=ERROR,
            anchor="w",
        ).pack(anchor="w")
        self._tbl_error = ctk.CTkLabel(
            self._tbl_error_inner,
            text="",
            font=font("body"),
            text_color="#fecaca",
            anchor="w",
            justify="left",
            wraplength=780,
        )
        self._tbl_error.pack(anchor="w", fill="x", pady=(2, 0))
        # Скрыт, пока нет ошибки
        self._tbl_error_visible = False

        self._table_text = ctk.CTkTextbox(
            tab, font=("Consolas", 12), fg_color=BG_CARD, border_color=BORDER, border_width=1,
            text_color=TEXT, wrap="none",
        )
        self._table_text.grid(row=2, column=0, sticky="nsew")
        self._on_table_axis_change()

        def _refit_err(_e=None) -> None:
            w = max(320, int(tab.winfo_width()) - 48)
            self._tbl_error.configure(wraplength=w)

        tab.bind("<Configure>", _refit_err)

    # ── UI helpers ────────────────────────────────────────────────────────

    def _split_panes(self, tab: ctk.CTkFrame) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        """Две колонки: слева ввод без полосы прокрутки, справа карточка результатов."""
        tab.grid_columnconfigure(0, weight=0, minsize=PANE_LEFT_MIN)
        tab.grid_columnconfigure(1, weight=1, minsize=PANE_RIGHT_MIN)
        tab.grid_rowconfigure(0, weight=1)

        left = self._card(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, PAD["sm"]))

        # Обёртка: карточка + полоса прокрутки справа за границей карточки
        outer = ctk.CTkFrame(tab, fg_color="transparent")
        outer.grid(row=0, column=1, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        right = self._card(outer)
        right.grid(row=0, column=0, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        right._results_outer = outer  # type: ignore[attr-defined]
        return left, right

    @staticmethod
    def _card(parent: ctk.CTkFrame) -> ctk.CTkFrame:
        return ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=RADIUS["md"], border_width=1, border_color=BORDER)

    def _results_scroll(self, right: ctk.CTkFrame) -> ctk.CTkScrollableFrame:
        """Прокручиваемая область результатов (стандартный ползунок CTk)."""
        scroll = ctk.CTkScrollableFrame(
            right,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
            **SCROLLBAR,
        )
        return scroll

    def _option_menu(self, parent: Any, **kwargs: Any) -> ctk.CTkOptionMenu:
        """OptionMenu, чьё выпадающее меню не уходит за край экрана."""
        menu = ctk.CTkOptionMenu(parent, **OPTION_MENU, **kwargs)
        self._clamp_dropdown(menu)
        return menu

    @staticmethod
    def _clamp_dropdown(menu: ctk.CTkOptionMenu) -> None:
        def _open() -> None:
            values = getattr(menu, "_values", []) or []
            item_h = 26
            est_h = max(item_h, len(values) * item_h + 8)
            screen_w = menu.winfo_screenwidth()
            screen_h = menu.winfo_screenheight()
            btn_x = menu.winfo_rootx()
            btn_y = menu.winfo_rooty()
            btn_h = menu.winfo_height()
            btn_w = max(menu.winfo_width(), 120)

            y_below = btn_y + btn_h
            if y_below + est_h > screen_h - 12:
                y = max(8, btn_y - est_h)
            else:
                y = y_below

            x = btn_x
            if x + btn_w > screen_w - 8:
                x = max(8, screen_w - btn_w - 8)
            x = max(8, x)
            menu._dropdown_menu.open(x, y)  # type: ignore[attr-defined]

        menu._open_dropdown_menu = _open  # type: ignore[method-assign]
    def _field(self, parent: ctk.CTkFrame, label: str, unit: str, var: ctk.StringVar) -> None:
        ctk.CTkLabel(parent, text=label, font=font("label"), text_color=TEXT).pack(anchor="w", pady=(PAD["sm"], 0))
        ctk.CTkLabel(parent, text=unit, font=font("small"), text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkEntry(
            parent,
            textvariable=var,
            width=220,
            height=34,
            font=font("label"),
            fg_color=BG_INPUT,
            border_color=BORDER,
            text_color=TEXT,
        ).pack(anchor="w", pady=(PAD["xs"], 0))

    def _field_with_unit(
        self,
        parent: ctk.CTkFrame,
        label: str,
        var: ctk.StringVar,
        *,
        kind: str,
    ) -> None:
        ctk.CTkLabel(parent, text=label, font=font("label"), text_color=TEXT).pack(anchor="w", pady=(PAD["sm"], 0))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(PAD["xs"], 0))
        ctk.CTkEntry(
            row,
            textvariable=var,
            width=160,
            height=34,
            font=font("label"),
            fg_color=BG_INPUT,
            border_color=BORDER,
            text_color=TEXT,
        ).pack(side="left")
        if kind == "pressure":
            self._option_menu(
                row,
                variable=self._p_unit_var,
                values=[u.value for u in PressureUnit],
                font=font("small"),
                width=130,
            ).pack(side="left", padx=(PAD["sm"], 0))
        else:
            self._option_menu(
                row,
                variable=self._t_unit_var,
                values=[u.value for u in TemperatureUnit],
                font=font("small"),
                width=80,
            ).pack(side="left", padx=(PAD["sm"], 0))

    def _apply_block(
        self,
        parent: ctk.CTkFrame,
        buttons: list[tuple[str, str]],
        command_factory: Any,
    ) -> None:
        frame = ctk.CTkFrame(parent, fg_color=BG_CARD_SOFT, corner_radius=RADIUS["sm"])
        frame.pack(fill="x", padx=PAD["md"], pady=(0, PAD["md"]))
        ctk.CTkLabel(frame, text="Подставить в тепловой баланс", font=font("small"), text_color=TEXT_MUTED).pack(
            anchor="w", padx=PAD["sm"], pady=(PAD["sm"], PAD["xs"])
        )
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=PAD["sm"], pady=(0, PAD["sm"]))
        for i, (label, key) in enumerate(buttons):
            ctk.CTkButton(
                row, text=label, height=30, font=font("small"),
                command=lambda k=key: command_factory(k), **BTN_APPLY,
            ).grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, PAD["xs"]), pady=PAD["xs"])
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)
    # ── Логика: состояние ─────────────────────────────────────────────────

    def _current_mode(self) -> InputMode:
        return InputMode(self._mode_var.get())

    def _current_p_unit(self) -> PressureUnit:
        return PressureUnit(self._p_unit_var.get())

    def _current_t_unit(self) -> TemperatureUnit:
        return TemperatureUnit(self._t_unit_var.get())

    def _on_unit_change(self, _choice: str | None = None) -> None:
        mode = self._current_mode()
        k1, k2 = input_kinds(mode)
        u1, u2 = input_units(mode, self._current_p_unit(), self._current_t_unit())
        if k1 == "other":
            self._in1_unit.configure(text=u1)
        if k2 == "other":
            self._in2_unit.configure(text=u2)

    def _on_mode_change(self, _choice: str | None = None) -> None:
        mode = self._current_mode()
        l1, l2 = input_labels(mode)
        k1, k2 = input_kinds(mode)
        u1, u2 = input_units(mode, self._current_p_unit(), self._current_t_unit())
        d1, d2 = default_inputs(mode)

        for w in (
            self._in1_label,
            self._in1_unit,
            self._in1_row,
            self._in2_label,
            self._in2_unit,
            self._in2_row,
            self._p_unit_menu,
            self._t_unit_menu,
            self._p_unit_menu_2,
            self._t_unit_menu_2,
            self._in1_entry,
            self._in2_entry,
        ):
            w.pack_forget()

        self._in1_var.set(d1)
        self._in1_label.configure(text=l1)
        self._in1_label.pack(anchor="w", pady=(PAD["sm"], 0))
        self._in1_row.pack(fill="x", pady=(PAD["xs"], 0))
        self._in1_entry.pack(side="left")
        if k1 == "pressure":
            self._p_unit_menu.pack(side="left", padx=(PAD["sm"], 0))
        elif k1 == "temperature":
            self._t_unit_menu.pack(side="left", padx=(PAD["sm"], 0))
        elif u1:
            self._in1_unit.configure(text=u1)
            self._in1_unit.pack(side="left", padx=(PAD["sm"], 0))

        if l2 and k2 != "none":
            self._in2_var.set(d2)
            self._in2_label.configure(text=l2)
            self._in2_label.pack(anchor="w", pady=(PAD["md"], 0))
            self._in2_row.pack(fill="x", pady=(PAD["xs"], 0))
            self._in2_entry.pack(side="left")
            if k2 == "pressure":
                self._p_unit_menu_2.pack(side="left", padx=(PAD["sm"], 0))
            elif k2 == "temperature":
                self._t_unit_menu_2.pack(side="left", padx=(PAD["sm"], 0))
            elif u2:
                self._in2_unit.configure(text=u2)
                self._in2_unit.pack(side="left", padx=(PAD["sm"], 0))
        else:
            self._in2_var.set("")
        self._state_error.configure(text="")

    def _parse_state_inputs(self) -> dict[str, float]:
        mode = self._current_mode()
        v1 = parse_float(self._in1_var.get())
        p_unit = self._current_p_unit()
        t_unit = self._current_t_unit()

        if mode == InputMode.P_SAT:
            return {"p_mpa": pressure_to_mpa(v1, p_unit)}
        if mode == InputMode.T_SAT:
            return {"t_c": temperature_to_c(v1, t_unit)}

        v2 = parse_float(self._in2_var.get())
        if mode == InputMode.PT:
            return {"p_mpa": pressure_to_mpa(v1, p_unit), "t_c": temperature_to_c(v2, t_unit)}
        if mode in (InputMode.PX, InputMode.PH, InputMode.PS):
            return {"p_mpa": pressure_to_mpa(v1, p_unit), **_second_arg(mode, v2)}
        if mode in (InputMode.TX, InputMode.TS):
            return {"t_c": temperature_to_c(v1, t_unit), **_second_arg(mode, v2)}
        if mode == InputMode.HS:
            return {"h_kj": v1, "s_kj": v2}
        raise SteamCalculationError("Неизвестный режим")

    def _calc_state(self) -> None:
        self._state_error.configure(text="")
        try:
            result = calculate_state(self._current_mode(), **self._parse_state_inputs())
        except (SteamCalculationError, ValueError) as exc:
            self._state_error.configure(text=format_iapws_error(exc, context="Состояние"))
            return

        self._last_state = result
        self._render_results(self._state_scroll, result.as_result_rows())
        self._add_history(f"Состояние [{self._mode_var.get()}]: h={result.h_kj:.2f} кДж/кг")

        try:
            sat = saturation_by_pressure(result.p_mpa)
            self._append_sat_hint(result, sat)
        except SteamCalculationError:
            pass

    def _append_sat_hint(self, state: SteamProperties, sat: SaturationProperties) -> None:
        hint = ctk.CTkFrame(self._state_scroll, fg_color=BG_CARD_SOFT, corner_radius=RADIUS["sm"])
        hint.pack(fill="x", pady=(PAD["md"], 0))
        ctk.CTkLabel(hint, text="Линия насыщения при данном p", font=font("small"), text_color=TEXT_MUTED).pack(
            anchor="w", padx=PAD["sm"], pady=(PAD["sm"], 0)
        )
        lines = [
            f"{N.T_nas} = {sat.t_c:.2f} °C",
            f"{N.h_l} = {sat.h_l:.2f}  |  {N.h_v} = {sat.h_v:.2f} кДж/кг",
            f"r = {sat.r:.2f} кДж/кг",
        ]
        if state.superheat_c and state.superheat_c > 0.01:
            lines.append(f"Перегрев Δt = {state.superheat_c:.2f} °C")
        elif state.subcooling_c and state.subcooling_c > 0.01:
            lines.append(f"Недогрев Δt = {state.subcooling_c:.2f} °C")
        ctk.CTkLabel(hint, text="\n".join(lines), font=font("label"), text_color=TEXT, justify="left").pack(
            anchor="w", padx=PAD["sm"], pady=(PAD["xs"], PAD["sm"])
        )

    def _clear_state(self) -> None:
        self._on_mode_change()
        for child in self._state_scroll.winfo_children():
            child.destroy()
        self._last_state = None
        self._state_result_rows = []
        self._state_error.configure(text="")

    def _copy_state(self) -> None:
        if not self._last_state:
            self._state_error.configure(text="Сначала выполните расчёт")
            return
        self._copy_clipboard(self._last_state.as_text_block())
        self._flash_status("Скопировано", error_label=self._state_error)

    # ── Логика: котёл ─────────────────────────────────────────────────────

    def _toggle_boiler_steam_mode(self) -> None:
        wet = self._boiler_wet_var.get()
        self._boiler_t_sh_frame.pack_forget()
        self._boiler_x_frame.pack_forget()
        if wet:
            self._boiler_x_frame.pack(fill="x")
        else:
            self._boiler_t_sh_frame.pack(fill="x")

    def _calc_boiler(self) -> None:
        self._boiler_error.configure(text="")
        try:
            p_mpa = pressure_to_mpa(parse_float(self._boiler_p_var.get()), self._current_p_unit())
            t_fw = temperature_to_c(parse_float(self._boiler_t_fw_var.get()), self._current_t_unit())
            if self._boiler_wet_var.get():
                x_text = self._boiler_x_var.get().strip()
                if not x_text:
                    raise SteamCalculationError("Укажите качество пара x")
                result = calculate_boiler_cycle(p_mpa=p_mpa, t_feedwater_c=t_fw, x_steam=parse_float(x_text))
            else:
                t_sh = temperature_to_c(parse_float(self._boiler_t_sh_var.get()), self._current_t_unit())
                result = calculate_boiler_cycle(p_mpa=p_mpa, t_feedwater_c=t_fw, t_superheat_c=t_sh)
        except (SteamCalculationError, ValueError) as exc:
            self._boiler_error.configure(text=format_iapws_error(exc, context="Котёл"))
            return

        self._last_boiler = result
        self._render_results(self._boiler_scroll, result.as_result_rows())
        self._add_history(
            f"Котёл p={result.p_mpa:.2f} МПа: i_pe={result.i_pe:.0f}, i_pv={result.i_pv:.0f}, i_sat={result.i_sat:.0f}"
        )

    def _apply_boiler_all(self) -> None:
        if not self._last_boiler:
            self._boiler_error.configure(text="Сначала выполните расчёт котла")
            return
        self._push_to_host(self._last_boiler.enthalpies_for_balance())

    # ── Логика: насыщение ─────────────────────────────────────────────────

    def _on_sat_mode_change(self) -> None:
        self._sat_unit_menu.pack_forget()
        self._sat_t_unit_menu.pack_forget()
        by_p = self._sat_mode_var.get() == SaturationInput.BY_PRESSURE.value
        prev = getattr(self, "_sat_mode_prev", None)
        if by_p:
            self._sat_label.configure(text="Давление")
            self._sat_unit_menu.pack(side="left", padx=(PAD["sm"], 0))
            if prev != SaturationInput.BY_PRESSURE.value:
                self._sat_var.set("4.0")
        else:
            self._sat_label.configure(text="Температура")
            self._sat_t_unit_menu.pack(side="left", padx=(PAD["sm"], 0))
            if prev != SaturationInput.BY_TEMPERATURE.value:
                self._sat_var.set("250.0")
        self._sat_mode_prev = self._sat_mode_var.get()
        self._sat_error.configure(text="")

    def _calc_saturation(self) -> None:
        self._sat_error.configure(text="")
        try:
            val = parse_float(self._sat_var.get())
            if self._sat_mode_var.get() == SaturationInput.BY_PRESSURE.value:
                result = saturation_by_pressure(pressure_to_mpa(val, self._current_p_unit()))
            else:
                result = saturation_by_temperature(temperature_to_c(val, self._current_t_unit()))
        except (SteamCalculationError, ValueError) as exc:
            self._sat_error.configure(text=format_iapws_error(exc, context="Насыщение"))
            return

        self._last_sat = result
        self._render_results(self._sat_scroll, result.as_result_rows())
        self._add_history(f"Насыщение: p={result.p_mpa:.3f} МПа, T={result.t_c:.1f} °C")

    def _apply_sat_button(self, key: str) -> None:
        if not self._last_sat:
            self._sat_error.configure(text="Сначала выполните расчёт насыщения")
            return
        if key == "i_sat_l":
            self._push_to_host({"i_sat": self._last_sat.h_l})
        elif key == "i_pe_v":
            self._push_to_host({"i_pe": self._last_sat.h_v})

    # ── Логика: таблица ───────────────────────────────────────────────────

    def _show_tbl_error(self, message: str, *, ok: bool = False) -> None:
        """Показать баннер ошибки/статуса под панелью параметров таблицы."""
        if ok:
            self._tbl_error_frame.configure(fg_color="#132e1e", border_color=SUCCESS)
            self._tbl_error_inner.winfo_children()[0].configure(text="Готово", text_color=SUCCESS)
            self._tbl_error.configure(text=message, text_color="#bbf7d0")
        else:
            self._tbl_error_frame.configure(fg_color="#3f1d1d", border_color=ERROR)
            self._tbl_error_inner.winfo_children()[0].configure(text="Ошибка", text_color=ERROR)
            self._tbl_error.configure(text=message, text_color="#fecaca")
        if not self._tbl_error_visible:
            self._tbl_error_frame.grid(row=1, column=0, sticky="ew", pady=(0, PAD["sm"]))
            self._tbl_error_visible = True

    def _hide_tbl_error(self) -> None:
        if self._tbl_error_visible:
            self._tbl_error_frame.grid_forget()
            self._tbl_error_visible = False
        self._tbl_error.configure(text="")

    def _on_table_axis_change(self, _choice: str | None = None) -> None:
        axis = self._tbl_axis_map.get(self._tbl_axis_var.get(), TableAxis.BY_PRESSURE.value)
        if axis == TableAxis.BY_PRESSURE.value:
            self._tbl_start_label.configure(text=f"От [{self._p_unit_var.get()}]")
            self._tbl_end_label.configure(text=f"До [{self._p_unit_var.get()}]")
            self._tbl_start_var.set("0.1")
            self._tbl_end_var.set("10")
        else:
            tu = self._t_unit_var.get()
            self._tbl_start_label.configure(text=f"От [{tu}]")
            self._tbl_end_label.configure(text=f"До [{tu}]")
            self._tbl_start_var.set("50")
            self._tbl_end_var.set("350")
        self._hide_tbl_error()

    def _calc_table(self) -> None:
        self._hide_tbl_error()
        try:
            axis = TableAxis(self._tbl_axis_map.get(self._tbl_axis_var.get(), TableAxis.BY_PRESSURE.value))
            n = int(parse_float(self._tbl_n_var.get()))
            start = parse_float(self._tbl_start_var.get())
            end = parse_float(self._tbl_end_var.get())
            if axis == TableAxis.BY_TEMPERATURE:
                start = temperature_to_c(start, self._current_t_unit())
                end = temperature_to_c(end, self._current_t_unit())
            rows = generate_saturation_table(
                axis=axis,
                start=start,
                end=end,
                n_points=n,
                pressure_unit=self._current_p_unit(),
            )
            text = saturation_table_as_text(rows, pressure_unit=self._current_p_unit())
        except (SteamCalculationError, ValueError) as exc:
            self._show_tbl_error(format_iapws_error(exc, context="Таблица"))
            return

        self._last_table_text = text
        self._table_text.delete("1.0", "end")
        self._table_text.insert("1.0", text)
        self._add_history(f"Таблица насыщения: {n} точек")

    def _copy_table(self) -> None:
        if not self._last_table_text:
            self._show_tbl_error("Сначала постройте таблицу")
            return
        self._copy_clipboard(self._last_table_text)
        self._show_tbl_error("Таблица скопирована", ok=True)
        self.win.after(2500, self._hide_tbl_error)

    # ── Интеграция с главным окном ────────────────────────────────────────

    def _load_from_balance(self) -> None:
        """Показать свойства по энтальпиям из формы — не сбрасывая текущий расчёт плагина."""
        if not hasattr(self._host, "get_steam_form_values"):
            self._state_error.configure(text="Чтение из баланса недоступно")
            return
        try:
            if hasattr(self._host, "highlight_steam_source_fields"):
                self._host.highlight_steam_source_fields()
            vals = self._host.get_steam_form_values()
            p_mpa = pressure_to_mpa(parse_float(self._boiler_p_var.get()), self._current_p_unit())
            balance_rows: list[tuple[str, str, str]] = [
                ("Из баланса", "Давление (из вкладки Котёл)", f"{p_mpa:.4f} МПа")
            ]
            last_from_balance: SteamProperties | None = None
            for label, key in [
                (N.i_pe, "i_pe"),
                (N.i_pv, "i_pv"),
                (N.i_sat, "i_sat"),
                (N.i_phi, "i_phi"),
            ]:
                h = vals.get(key)
                if h is None:
                    continue
                state = calculate_from_enthalpy(p_mpa, h)
                last_from_balance = state
                balance_rows.append((label, "h", f"{h:.2f} кДж/кг"))
                balance_rows.append((label, "T", f"{state.t_c:.2f} °C"))
                balance_rows.append((label, "s", f"{state.s_kj:.4f} кДж/(кг·K)"))
                if state.x is not None:
                    balance_rows.append((label, "x", f"{state.x:.4f}"))

            # Сохраняем предыдущий расчёт Состояния, если был
            kept_state = self._last_state
            kept_rows = list(getattr(self, "_state_result_rows", []) or [])

            combined: list[tuple[str, str, str]] = []
            if kept_rows:
                combined.extend(kept_rows)
            combined.extend(balance_rows)

            self.tabs.set("Состояние")
            self._render_results(self._state_scroll, combined)
            # Не затираем рабочий расчёт плагина
            if kept_state is not None:
                self._last_state = kept_state
            elif last_from_balance is not None:
                self._last_state = last_from_balance

            self._add_history("Загружено из теплового баланса")
            self._flash_status(
                "Взяты энтальпии из формы: i_пе, i_пв, i_нас, i_φ — свойства справа. "
                "Поля-источники в главном окне подсвечены ~15 с"
            )
            self.win.lift()
            self.win.focus_force()
        except (SteamCalculationError, ValueError, KeyError) as exc:
            self._state_error.configure(text=format_iapws_error(exc, context="Из баланса"))

    def _open_wsp(self) -> None:
        try:
            launch_wsp()
            self._flash_status("Запущен WaterSteamPro Calculator")
        except SteamCalculationError as exc:
            self._state_error.configure(text=str(exc))

    def _apply_enthalpy(self, field: str) -> None:
        if not self._last_state:
            self._state_error.configure(text="Сначала выполните расчёт")
            return
        self._push_to_host({field: self._last_state.h_kj})

    def _push_to_host(self, values: dict[str, float]) -> None:
        if hasattr(self._host, "apply_steam_values"):
            # Сохраняем снимок результатов — подстановка в главное окно их не должна сбрасывать
            preserved_state = self._last_state
            preserved_rows = list(getattr(self, "_state_result_rows", []) or [])
            preserved_boiler = self._last_boiler
            preserved_sat = self._last_sat

            self._host.apply_steam_values(values)

            if preserved_state is not None:
                self._last_state = preserved_state
            if preserved_boiler is not None:
                self._last_boiler = preserved_boiler
            if preserved_sat is not None:
                self._last_sat = preserved_sat
            if preserved_rows and self._state_scroll.winfo_exists():
                # Если кто-то очистил панель — восстановить
                if not self._state_scroll.winfo_children():
                    self._render_results(self._state_scroll, preserved_rows)
                else:
                    self._state_result_rows = preserved_rows

            self.win.lift()
            self.win.after(50, self.win.focus_force)
            self._flash_status("Подставлено в тепловой баланс")
        else:
            self._state_error.configure(text="Интеграция с главным окном недоступна")

    # ── Общие утилиты ─────────────────────────────────────────────────────

    def _render_results(self, container: ctk.CTkScrollableFrame, rows: list[tuple[str, str, str]]) -> None:
        for child in container.winfo_children():
            child.destroy()

        if container is self._state_scroll:
            self._state_result_rows = list(rows)

        container.update_idletasks()
        avail = max(260, int(container.winfo_width()) - 36)
        wrap_param = max(120, avail // 2)
        wrap_value = max(120, avail - wrap_param - 24)

        current_group = ""
        for group, param, value in rows:
            if group != current_group:
                current_group = group
                ctk.CTkLabel(container, text=group, font=font("label"), text_color=ACCENT).pack(
                    anchor="w", pady=(PAD["md"], PAD["xs"]), padx=(0, PAD["lg"])
                )
            row = ctk.CTkFrame(container, fg_color="transparent")
            row.pack(fill="x", pady=1, padx=(0, PAD["sm"]))
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=0)
            ctk.CTkLabel(
                row,
                text=param,
                font=font("small"),
                text_color=TEXT_MUTED,
                anchor="w",
                wraplength=wrap_param,
                justify="left",
            ).grid(row=0, column=0, sticky="ew")
            ctk.CTkLabel(
                row,
                text=value,
                font=font("label"),
                text_color=TEXT,
                anchor="e",
                wraplength=wrap_value,
                justify="right",
            ).grid(row=0, column=1, sticky="e", padx=(PAD["sm"], 0))

        def _refit(_event: Any = None) -> None:
            width = max(260, int(container.winfo_width()) - 36)
            wp = max(120, width // 2)
            wv = max(120, width - wp - 24)
            for child in container.winfo_children():
                if not isinstance(child, ctk.CTkFrame):
                    continue
                labels = [c for c in child.winfo_children() if isinstance(c, ctk.CTkLabel)]
                if len(labels) >= 2:
                    labels[0].configure(wraplength=wp)
                    labels[1].configure(wraplength=wv)

        container.bind("<Configure>", _refit)
        container.update_idletasks()
        try:
            canvas = container._parent_canvas  # type: ignore[attr-defined]
            canvas.yview_moveto(0)
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass
    def _copy_clipboard(self, text: str) -> None:
        self.win.clipboard_clear()
        self.win.clipboard_append(text)

    def _add_history(self, line: str) -> None:
        self._history.append(line)
        if len(self._history) > 20:
            self._history.pop(0)

    def _flash_status(self, message: str, error_label: ctk.CTkLabel | None = None) -> None:
        targets = [self._state_error, self._sat_error, self._boiler_error]
        if error_label is not None and error_label not in targets:
            targets.append(error_label)
        for lbl in targets:
            if lbl is not None:
                lbl.configure(text=message, text_color=SUCCESS)
        self.win.after(2500, self._clear_status)

    def _clear_status(self) -> None:
        for lbl in (self._state_error, self._sat_error, self._boiler_error):
            lbl.configure(text="", text_color=ERROR)
        if getattr(self, "_tbl_error", None) is not None:
            # Не трогаем баннер таблицы, если там реальная ошибка — только сброс «успеха»
            if self._tbl_error.cget("text_color") == SUCCESS or self._tbl_error.cget("text") in (
                "Таблица скопирована",
            ):
                self._hide_tbl_error()


def _second_arg(mode: InputMode, v2: float) -> dict[str, float]:
    mapping = {
        InputMode.PT: {"t_c": v2},
        InputMode.PX: {"x": v2},
        InputMode.PH: {"h_kj": v2},
        InputMode.PS: {"s_kj": v2},
        InputMode.TX: {"x": v2},
        InputMode.TS: {"s_kj": v2},
    }
    return mapping.get(mode, {})


def create_plugin() -> SteamQualityPlugin:
    return SteamQualityPlugin()
