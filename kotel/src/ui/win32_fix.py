"""Исправления поведения окна и производительности на Windows."""

from __future__ import annotations

import sys


def apply_windows_fixes() -> None:
    """Стабильное перемещение окна и отключение фоновых циклов CustomTkinter."""
    import customtkinter as ctk
    from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

    # Не перерисовывать titlebar (withdraw/deiconify ломает позицию окна)
    ctk.CTk._deactivate_windows_window_header_manipulation = True
    ctk.CTkToplevel._deactivate_windows_window_header_manipulation = True

    # Фиксированный масштаб 1:1 — стабильнее при перетаскивании
    ScalingTracker.deactivate_automatic_dpi_awareness = True
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)

    # Остановить фоновый опрос DPI каждые 100 мс
    ScalingTracker.check_dpi_scaling = classmethod(lambda cls: None)  # type: ignore[assignment]
    ScalingTracker.update_loop_running = True

    if not sys.platform.startswith("win"):
        ctk.set_appearance_mode("light")
        return

    ctk.set_appearance_mode("light")

    # Остановить цикл AppearanceModeTracker (system mode)
    try:
        from customtkinter.windows.widgets.appearance_mode.appearance_mode_tracker import (
            AppearanceModeTracker,
        )

        AppearanceModeTracker.appearance_mode_set_by = "custom"
        AppearanceModeTracker.update_loop_running = True

        def _noop_appearance_update(cls) -> None:
            pass

        AppearanceModeTracker.update = classmethod(_noop_appearance_update)  # type: ignore[assignment]
    except Exception:
        pass
