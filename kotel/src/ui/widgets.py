"""Вспомогательные виджеты UI — промышленный high-tech стиль."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from .theme import (
    ACCENT,
    ACCENT_GLOW,
    ACCENT_HOVER,
    ACCENT_SOFT,
    BG_BADGE,
    BG_CARD,
    BG_CARD_HOVER,
    BG_CARD_SOFT,
    BG_INPUT,
    BG_MAIN,
    BG_SIDEBAR,
    BORDER,
    BORDER_GLOW,
    BORDER_LIGHT,
    CYAN,
    CYAN_GLOW,
    CYAN_MUTED,
    CYAN_SOFT,
    MPL_AXES,
    MPL_FACE,
    MPL_GRID,
    MPL_SPINE,
    MPL_TEXT,
    PAD,
    RADIUS,
    TEXT,
    TEXT_DIM,
    TEXT_MUTED,
    TEXT_ON_ACCENT,
    WARNING,
    font,
)


class LabeledEntry(ctk.CTkFrame):
    """Поле ввода с подписью (полный или компактный режим)."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        label: str = "",
        default: str = "0",
        width: int = 130,
        tooltip: str = "",
        *,
        symbol: str = "",
        description: str = "",
        unit: str = "",
        label_mode: str = "full",
        accent: str = "default",
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self._symbol = symbol
        self._description = description
        self._unit = unit
        self._extra_tooltip = tooltip
        self._label_mode = label_mode if label_mode in ("full", "compact") else "full"
        self._accent = accent
        self._border_idle = CYAN if accent == "cyan" else (ACCENT if accent == "orange" else BORDER)
        self._legacy_label = label if not symbol else ""

        self._lbl = ctk.CTkLabel(
            self,
            text="",
            anchor="w",
            font=font("label"),
            text_color=TEXT,
            wraplength=520,
            justify="left",
        )
        self._lbl.grid(row=0, column=0, sticky="w", padx=(0, PAD["md"]))

        self.var = ctk.StringVar(value=default)
        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.var,
            width=width,
            height=34,
            corner_radius=RADIUS["sm"],
            font=font("mono"),
            fg_color=BG_INPUT,
            border_color=self._border_idle,
            border_width=1,
            text_color=TEXT,
        )
        self.entry.grid(row=0, column=1, sticky="e")
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

        self._highlight_after: str | None = None
        self._highlight_pulses = 0
        self._apply_label_mode(self._label_mode)

    def _on_focus_in(self, _event=None) -> None:
        if self._highlight_pulses > 0:
            return
        glow = CYAN_GLOW if self._accent == "cyan" else (ACCENT_GLOW if self._accent == "orange" else CYAN)
        self.entry.configure(border_color=glow, border_width=2)

    def _on_focus_out(self, _event=None) -> None:
        if self._highlight_pulses > 0:
            return
        self.entry.configure(border_color=self._border_idle, border_width=1)

    def get_float(self, default: float = 0.0) -> float:
        try:
            return float(self.var.get().replace(",", "."))
        except ValueError:
            return default

    def get_bool(self) -> bool:
        return self.var.get().lower() in ("1", "true", "да", "yes")

    def set_value(self, value: str | float) -> None:
        self.var.set(str(value))

    def flash_highlight(self, pulses: int = 8, interval_ms: int = 450) -> None:
        """Мигающая подсветка (кратко привлекает внимание)."""
        self.clear_highlight()
        self._highlight_pulses = pulses
        self.entry.bind("<FocusIn>", self._on_highlight_focus, add="+")
        self.entry.bind("<Button-1>", self._on_highlight_focus, add="+")
        self._pulse_highlight(interval_ms)

    def mark_changed(self, hold_ms: int = 12000) -> None:
        """
        Долгая пометка изменённого поля: остаётся видимой на любом шаге,
        пока пользователь не кликнет/не сфокусирует поле или не истечёт hold_ms.
        """
        self.clear_highlight()
        self._highlight_pulses = 0
        self.entry.configure(border_color=ACCENT_GLOW, fg_color=ACCENT_SOFT, border_width=2)
        self.entry.bind("<FocusIn>", self._on_highlight_focus, add="+")
        self.entry.bind("<Button-1>", self._on_highlight_focus, add="+")
        self._highlight_after = self.after(hold_ms, self.clear_highlight)

    def clear_highlight(self) -> None:
        if self._highlight_after:
            try:
                self.after_cancel(self._highlight_after)
            except Exception:
                pass
            self._highlight_after = None
        self._highlight_pulses = 0
        self.entry.configure(border_color=self._border_idle, fg_color=BG_INPUT, border_width=1)

    def _on_highlight_focus(self, _event=None) -> None:
        self.clear_highlight()

    def _pulse_highlight(self, interval_ms: int) -> None:
        if self._highlight_pulses <= 0:
            self.clear_highlight()
            return
        on = self._highlight_pulses % 2 == 0
        if on:
            self.entry.configure(border_color=ACCENT_GLOW, fg_color=ACCENT_SOFT, border_width=2)
        else:
            self.entry.configure(border_color=ACCENT, fg_color=BG_INPUT, border_width=2)
        self._highlight_pulses -= 1
        self._highlight_after = self.after(interval_ms, lambda: self._pulse_highlight(interval_ms))

    def set_label_mode(self, mode: str) -> None:
        if mode not in ("full", "compact"):
            mode = "full"
        self._label_mode = mode
        self._apply_label_mode(mode)

    def _caption_full(self) -> str:
        if self._legacy_label:
            return self._legacy_label
        if self._unit:
            return f"{self._symbol} — {self._description}, {self._unit}"
        if self._description:
            return f"{self._symbol} — {self._description}"
        return self._symbol

    def _caption_compact(self) -> str:
        if self._legacy_label and not self._symbol:
            parts = self._legacy_label.split(" — ", 1)
            return parts[0].strip() if parts else self._legacy_label
        if self._unit:
            return f"{self._symbol}, {self._unit}"
        return self._symbol

    def _tooltip_text(self) -> str:
        bits: list[str] = []
        if self._description:
            bits.append(self._description)
        elif self._legacy_label and " — " in self._legacy_label:
            bits.append(self._legacy_label.split(" — ", 1)[1].strip())
        if self._extra_tooltip:
            bits.append(self._extra_tooltip)
        return "\n".join(bits)

    def _apply_label_mode(self, mode: str) -> None:
        if mode == "compact":
            self._lbl.configure(text=self._caption_compact())
            tip = self._tooltip_text() or self._caption_full()
            self._bind_tooltip(self._lbl, tip)
            self._bind_tooltip(self.entry, tip)
        else:
            self._lbl.configure(text=self._caption_full())
            self._unbind_tooltip(self._lbl)
            self._unbind_tooltip(self.entry)
            if self._extra_tooltip:
                self._bind_tooltip(self._lbl, self._extra_tooltip)

    @staticmethod
    def _unbind_tooltip(widget: ctk.CTkBaseClass) -> None:
        for seq in ("<Enter>", "<Leave>", "<Button-1>"):
            widget.unbind(seq)

    @staticmethod
    def _bind_tooltip(widget: ctk.CTkBaseClass, text: str) -> None:
        if not text:
            return
        tip: ctk.CTkToplevel | None = None
        tip_after: str | None = None

        def hide(_event=None) -> None:
            nonlocal tip, tip_after
            if tip_after:
                widget.after_cancel(tip_after)
                tip_after = None
            if tip:
                tip.destroy()
                tip = None

        def show(_event=None) -> None:
            nonlocal tip, tip_after
            if tip or tip_after:
                return
            tip_after = widget.after(400, _show_tip)

        def _show_tip() -> None:
            nonlocal tip, tip_after
            tip_after = None
            if tip:
                return
            root = widget.winfo_toplevel()
            tip = ctk.CTkToplevel(root)
            tip.wm_overrideredirect(True)
            tip.attributes("-topmost", False)
            tip.transient(root)
            tip.configure(fg_color=BG_CARD)
            x = widget.winfo_rootx() + 10
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            tip.geometry(f"+{x}+{y}")
            frame = ctk.CTkFrame(
                tip,
                fg_color=BG_CARD,
                border_width=1,
                border_color=BORDER_GLOW,
                corner_radius=RADIUS["sm"],
            )
            frame.pack()
            ctk.CTkLabel(
                frame,
                text=text,
                font=font("body"),
                fg_color="transparent",
                text_color=TEXT,
                padx=10,
                pady=6,
            ).pack()

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)
        widget.bind("<Button-1>", hide)


class GlowCard(ctk.CTkFrame):
    """Карточка с subtle border glow (цвет без alpha — Tk ограничение)."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        glow: str = "default",
        **kwargs,
    ) -> None:
        # Tk не поддерживает #RRGGBBAA — имитируем glow приглушёнными solid-цветами
        border = BORDER_GLOW
        if glow == "orange":
            border = "#7c3a1a"
        elif glow == "cyan":
            border = "#0e4a5c"
        kwargs.setdefault("corner_radius", RADIUS["md"])
        kwargs.setdefault("fg_color", BG_CARD)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", border)
        super().__init__(master, **kwargs)


class SectionFrame(GlowCard):
    """Секция с заголовком и акцентной полосой."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str,
        subtitle: str = "",
        *,
        glow: str = "default",
        **kwargs,
    ) -> None:
        super().__init__(master, glow=glow, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        bar_color = CYAN if glow == "cyan" else (ACCENT if glow == "orange" else CYAN_MUTED)
        accent_bar = ctk.CTkFrame(self, width=3, height=40, corner_radius=2, fg_color=bar_color)
        accent_bar.place(x=0, y=8, relheight=0.85)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD["lg"], pady=(PAD["md"], PAD["sm"]))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=title, font=font("section"), anchor="w", text_color=TEXT).grid(
            row=0, column=0, sticky="w"
        )
        if subtitle:
            ctk.CTkLabel(
                header,
                text=subtitle,
                font=font("small"),
                text_color=TEXT_MUTED,
                anchor="w",
            ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        sep = ctk.CTkFrame(self, height=1, fg_color=BORDER_LIGHT)
        sep.grid(row=1, column=0, sticky="ew", padx=PAD["lg"])

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", padx=PAD["lg"], pady=(PAD["sm"], PAD["md"]))
        self.body.grid_columnconfigure(0, weight=1)


class NavButton(ctk.CTkFrame):
    """Кнопка навигации в боковой панели — инженерный стиль."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        label: str,
        step: str,
        command,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", cursor="hand2", height=40, **kwargs)
        self.grid_propagate(False)
        self.pack_propagate(False)
        self._command = command
        self._active = False
        self._label = label
        self._step = step

        self.inner = ctk.CTkFrame(self, fg_color="transparent", corner_radius=RADIUS["sm"], height=36)
        self.inner.pack(fill="both", expand=True, padx=2, pady=2)
        self.inner.pack_propagate(False)

        # Фиксированная колонка акцента — одинаковая ширина у всех пунктов
        self._bar = ctk.CTkFrame(self.inner, width=3, height=28, corner_radius=2, fg_color=BG_SIDEBAR)
        self._bar.pack(side="left", padx=(4, 0), pady=4)
        self._bar.pack_propagate(False)

        self.badge = ctk.CTkFrame(
            self.inner,
            width=36,
            height=28,
            corner_radius=RADIUS["sm"],
            fg_color=BG_BADGE,
            border_width=1,
            border_color=BORDER,
        )
        self.badge.pack(side="left", padx=(8, 8), pady=4)
        self.badge.pack_propagate(False)

        self.step_label = ctk.CTkLabel(
            self.badge,
            text=step,
            text_color=TEXT_MUTED,
            font=font("step"),
            fg_color="transparent",
        )
        self.step_label.place(relx=0.5, rely=0.5, anchor="center")

        self.text_label = ctk.CTkLabel(
            self.inner,
            text=label,
            anchor="w",
            font=font("nav"),
            text_color=TEXT_MUTED,
        )
        self.text_label.pack(side="left", fill="x", expand=True, padx=(0, 8))

        for w in (self, self.inner, self.badge, self.step_label, self.text_label, self._bar):
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_click(self, _event=None) -> None:
        self._command()

    def _on_enter(self, _event=None) -> None:
        if not self._active:
            self.inner.configure(fg_color=BG_CARD_HOVER)

    def _on_leave(self, _event=None) -> None:
        if not self._active:
            self.inner.configure(fg_color="transparent")

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self.inner.configure(fg_color=BG_CARD)
            self._bar.configure(fg_color=ACCENT)
            self.badge.configure(fg_color=ACCENT, border_color=ACCENT_GLOW)
            self.step_label.configure(text_color=TEXT_ON_ACCENT)
            self.text_label.configure(text_color=TEXT, font=font("nav_active"))
        else:
            self.inner.configure(fg_color="transparent")
            self._bar.configure(fg_color=BG_SIDEBAR)
            self.badge.configure(fg_color=BG_BADGE, border_color=BORDER)
            self.step_label.configure(text_color=TEXT_MUTED)
            self.text_label.configure(text_color=TEXT_MUTED, font=font("nav"))


class SidebarNavItem(ctk.CTkButton):
    """Плоский пункт сайдбара для утилит / настроек."""

    def __init__(self, master, text: str, command=None, *, active: bool = False, **kwargs):
        super().__init__(
            master,
            text=text,
            anchor="w",
            height=34,
            corner_radius=RADIUS["sm"],
            font=font("nav"),
            fg_color=BG_CARD if active else "transparent",
            hover_color=BG_CARD_HOVER,
            text_color=TEXT if active else TEXT_MUTED,
            border_width=0,
            command=command,
            **kwargs,
        )


class MetricCard(GlowCard):
    """Карточка ключевого показателя."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str,
        unit: str,
        accent: bool = False,
        *,
        tone: str = "orange",
        **kwargs,
    ) -> None:
        glow = "orange" if (accent or tone == "orange") else ("cyan" if tone == "cyan" else "default")
        super().__init__(master, glow=glow, **kwargs)

        if accent:
            self.configure(fg_color=ACCENT_SOFT if tone != "cyan" else CYAN_SOFT)

        title_color = TEXT_MUTED
        value_color = ACCENT_GLOW if tone != "cyan" else CYAN_GLOW
        if accent:
            value_color = ACCENT_GLOW if tone != "cyan" else CYAN_GLOW

        # Accent strip — с отступом и скруглением, чтобы не вылезать за углы карточки
        strip_color = ACCENT if tone != "cyan" else CYAN
        strip = ctk.CTkFrame(
            self,
            height=3,
            corner_radius=2,
            fg_color=strip_color,
        )
        inset = max(RADIUS["md"] - 2, 6)
        strip.pack(fill="x", side="top", padx=inset, pady=(inset // 2, 0))
        strip.pack_propagate(False)

        ctk.CTkLabel(
            self,
            text=title.upper(),
            font=font("small"),
            text_color=title_color,
            anchor="w",
        ).pack(anchor="w", padx=PAD["md"], pady=(PAD["md"], 0))

        self.value_label = ctk.CTkLabel(
            self,
            text="—",
            font=font("metric"),
            text_color=value_color,
            anchor="w",
        )
        self.value_label.pack(anchor="w", padx=PAD["md"], pady=(2, 0))

        ctk.CTkLabel(
            self,
            text=unit,
            font=font("metric_unit"),
            text_color=TEXT_DIM,
            anchor="w",
        ).pack(anchor="w", padx=PAD["md"], pady=(0, PAD["md"]))

    def set(self, value: str) -> None:
        self.value_label.configure(text=value)


class ResultRow(ctk.CTkFrame):
    """Строка результата в таблице."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        label: str,
        unit: str = "",
        highlight: bool = False,
        *,
        tone: str = "default",
        **kwargs,
    ) -> None:
        bg = BG_CARD_SOFT if highlight else "transparent"
        super().__init__(master, fg_color=bg, corner_radius=RADIUS["sm"], **kwargs)
        self.grid_columnconfigure(1, weight=1)

        pad_y = PAD["sm"] if highlight else 3
        pad_x = PAD["sm"] if highlight else 0

        value_color = ACCENT_GLOW if highlight else (CYAN if tone == "cyan" else TEXT)

        ctk.CTkLabel(
            self,
            text=label,
            anchor="w",
            font=font("value") if highlight else font("label"),
            text_color=TEXT,
        ).grid(row=0, column=0, sticky="w", padx=(pad_x, PAD["md"]), pady=pad_y)

        self.value_label = ctk.CTkLabel(
            self,
            text="—",
            anchor="e",
            font=font("mono") if not highlight else font("value"),
            text_color=value_color,
        )
        self.value_label.grid(row=0, column=1, sticky="e", padx=(0, 4), pady=pad_y)

        if unit:
            ctk.CTkLabel(
                self,
                text=unit,
                anchor="w",
                width=56,
                font=font("small"),
                text_color=TEXT_DIM,
            ).grid(row=0, column=2, sticky="w", padx=(0, pad_x), pady=pad_y)

    def set(self, value: str) -> None:
        self.value_label.configure(text=value)


class InfoBox(GlowCard):
    """Блок рекомендаций или служебной информации."""

    def __init__(self, master: ctk.CTkBaseClass, title: str, **kwargs) -> None:
        super().__init__(master, glow="orange", **kwargs)
        self.configure(fg_color=BG_CARD_SOFT)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text=title,
            font=font("section"),
            anchor="w",
            text_color=ACCENT_GLOW,
        ).grid(row=0, column=0, sticky="w", padx=PAD["md"], pady=(PAD["md"], PAD["xs"]))

        self.text = ctk.CTkTextbox(
            self,
            height=120,
            font=font("body"),
            fg_color=BG_INPUT,
            text_color=TEXT,
            border_width=1,
            border_color=BORDER,
            activate_scrollbars=True,
            wrap="word",
        )
        self.text.grid(row=1, column=0, sticky="ew", padx=PAD["md"], pady=(0, PAD["md"]))

    def set_text(self, content: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")


class DataTable(GlowCard):
    """Таблица с поиском и сортировкой по клику на заголовок."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        columns: list[tuple[str, str, int]],
        *,
        height: int = 220,
        on_select: Callable[[dict], None] | None = None,
        **kwargs,
    ) -> None:
        """columns: list of (key, title, width)."""
        super().__init__(master, glow="cyan", **kwargs)
        self._columns = columns
        self._rows: list[dict[str, str]] = []
        self._filtered: list[dict[str, str]] = []
        self._sort_key: str | None = None
        self._sort_asc = True
        self._on_select = on_select
        self._row_widgets: list[ctk.CTkFrame] = []

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=PAD["md"], pady=(PAD["md"], PAD["sm"]))

        ctk.CTkLabel(toolbar, text="Поиск", font=font("small"), text_color=TEXT_MUTED).pack(
            side="left", padx=(0, PAD["sm"])
        )
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        search = ctk.CTkEntry(
            toolbar,
            textvariable=self._search_var,
            placeholder_text="Фильтр по любой колонке…",
            height=30,
            width=260,
            font=font("label"),
            fg_color=BG_INPUT,
            border_color=BORDER,
            text_color=TEXT,
        )
        search.pack(side="left", fill="x", expand=True)

        self._count_lbl = ctk.CTkLabel(toolbar, text="0", font=font("small"), text_color=TEXT_DIM)
        self._count_lbl.pack(side="right", padx=(PAD["sm"], 0))

        header = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        header.pack(fill="x", padx=PAD["md"])
        for i, (key, title, width) in enumerate(columns):
            btn = ctk.CTkButton(
                header,
                text=title,
                width=width,
                height=28,
                font=font("small"),
                fg_color="transparent",
                hover_color=BG_CARD_HOVER,
                text_color=CYAN,
                anchor="w",
                command=lambda k=key: self._sort_by(k),
            )
            btn.grid(row=0, column=i, sticky="ew", padx=1, pady=2)
            header.grid_columnconfigure(i, weight=1 if i == 0 else 0)

        self._body = ctk.CTkScrollableFrame(self, fg_color="transparent", height=height)
        self._body.pack(fill="both", expand=True, padx=PAD["md"], pady=(0, PAD["md"]))
        for i in range(len(columns)):
            self._body.grid_columnconfigure(i, weight=1 if i == 0 else 0)

    def set_rows(self, rows: list[dict[str, str]]) -> None:
        self._rows = rows
        self._apply_filter()

    def _sort_by(self, key: str) -> None:
        if self._sort_key == key:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_key = key
            self._sort_asc = True
        self._render()

    def _apply_filter(self) -> None:
        q = self._search_var.get().strip().lower()
        if not q:
            self._filtered = list(self._rows)
        else:
            self._filtered = [
                r
                for r in self._rows
                if any(q in str(r.get(c[0], "")).lower() for c in self._columns)
            ]
        self._render()

    def _render(self) -> None:
        for w in self._row_widgets:
            w.destroy()
        self._row_widgets.clear()

        data = list(self._filtered)
        if self._sort_key:

            def sort_key(row: dict) -> tuple:
                val = row.get(self._sort_key or "", "")
                try:
                    return (0, float(str(val).replace(",", ".")))
                except ValueError:
                    return (1, str(val).lower())

            data.sort(key=sort_key, reverse=not self._sort_asc)

        self._count_lbl.configure(text=f"{len(data)} / {len(self._rows)}")

        for idx, row in enumerate(data):
            bg = BG_CARD_SOFT if idx % 2 else "transparent"
            frame = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=0, cursor="hand2")
            frame.pack(fill="x", pady=0)
            self._row_widgets.append(frame)

            def make_click(r=row):
                return lambda _e=None: self._on_select and self._on_select(r)

            for i, (key, _title, width) in enumerate(self._columns):
                lbl = ctk.CTkLabel(
                    frame,
                    text=str(row.get(key, "")),
                    width=width,
                    anchor="w",
                    font=font("mono"),
                    text_color=TEXT,
                )
                lbl.grid(row=0, column=i, sticky="ew", padx=4, pady=4)
                frame.grid_columnconfigure(i, weight=1 if i == 0 else 0)
                lbl.bind("<Button-1>", make_click(row))
            frame.bind("<Button-1>", make_click(row))


class LossChart(GlowCard):
    """Встроенный matplotlib-график распределения потерь."""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs) -> None:
        super().__init__(master, glow="orange", **kwargs)
        self._mpl_canvas = None
        self._fig = None
        self._placeholder = ctk.CTkLabel(
            self,
            text="Выполните расчёт — здесь появится диаграмма потерь",
            font=font("body"),
            text_color=TEXT_MUTED,
        )
        self._placeholder.pack(expand=True, pady=PAD["xl"])

    def plot(self, labels: list[str], values: list[float]) -> None:
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
        except ImportError:
            self._placeholder.configure(text="Установите matplotlib для графиков")
            return

        if self._placeholder.winfo_exists():
            self._placeholder.pack_forget()

        if self._mpl_canvas is not None:
            self._mpl_canvas.get_tk_widget().destroy()
            self._mpl_canvas = None

        fig = Figure(figsize=(5.2, 2.8), dpi=100, facecolor=MPL_FACE)
        ax = fig.add_subplot(111)
        ax.set_facecolor(MPL_AXES)

        colors = [ACCENT, "#fb923c", CYAN, "#67e8f9", "#64748b", WARNING, "#94a3b8"]
        bars = ax.barh(labels, values, color=colors[: len(values)], height=0.62, edgecolor=BORDER)

        ax.invert_yaxis()
        vmax = max(values) if values else 1.0
        # Запас справа под подписи значений, чтобы не вылезали за край
        x_pad = max(vmax * 0.28, 1.8)
        ax.set_xlim(0, vmax + x_pad)
        ax.set_xlabel("%", color=MPL_TEXT, fontsize=9)
        ax.tick_params(colors=MPL_TEXT, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(MPL_SPINE)
        ax.xaxis.grid(True, color=MPL_GRID, linestyle="--", linewidth=0.6, alpha=0.8)
        ax.set_axisbelow(True)
        ax.set_title("Структура потерь тепла", color=TEXT, fontsize=10, pad=8, loc="left")

        for bar, val in zip(bars, values):
            width = bar.get_width()
            # Длинный столбец — подпись внутри, короткий — справа с отступом
            if vmax > 0 and width >= vmax * 0.55:
                x = width - vmax * 0.02
                ha = "right"
                color = TEXT
            else:
                x = width + x_pad * 0.08
                ha = "left"
                color = TEXT_MUTED
            ax.text(
                x,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}",
                va="center",
                ha=ha,
                color=color,
                fontsize=8,
                clip_on=True,
            )

        fig.subplots_adjust(left=0.22, right=0.96, top=0.88, bottom=0.16)
        self._fig = fig
        self._mpl_canvas = FigureCanvasTkAgg(fig, master=self)
        self._mpl_canvas.draw()
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=PAD["sm"], pady=PAD["sm"])


def make_scrollable_tab(parent: ctk.CTkFrame) -> ctk.CTkScrollableFrame:
    from .theme import SCROLLBAR

    frame = ctk.CTkScrollableFrame(
        parent,
        fg_color="transparent",
        **SCROLLBAR,
    )
    frame.grid(row=0, column=0, sticky="nsew", padx=PAD["lg"], pady=PAD["md"])
    frame.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)
    return frame


class PageHeader(ctk.CTkFrame):
    """Заголовок динамической области."""

    def __init__(self, master, title: str, subtitle: str = "", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=title, font=font("title"), text_color=TEXT, anchor="w").pack(
            anchor="w"
        )
        if subtitle:
            ctk.CTkLabel(
                self, text=subtitle, font=font("small"), text_color=TEXT_MUTED, anchor="w"
            ).pack(anchor="w", pady=(2, 0))

