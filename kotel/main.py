#!/usr/bin/env python3
"""Точка входа: расчёт теплового баланса котла."""

from __future__ import annotations

import sys
from pathlib import Path

# Корень проекта в PYTHONPATH
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.providers import JsonFileDataProvider
from src.plugins.registry import create_default_registry
from src.ui.win32_fix import apply_windows_fixes

apply_windows_fixes()

from src.ui.app import HeatBalanceApp


def main() -> None:
    data_provider = JsonFileDataProvider(ROOT / "data" / "reference")
    plugin_registry = create_default_registry(ROOT)
    app = HeatBalanceApp(ROOT, data_provider, plugin_registry)
    app.mainloop()


if __name__ == "__main__":
    main()
