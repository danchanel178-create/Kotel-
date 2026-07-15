"""Реестр и загрузка плагинов."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from .base import CalculationPlugin, PluginBase, UtilityPlugin


class PluginRegistry:
    """Реестр плагинов. Поддерживает загрузку из каталога plugins/."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginBase] = {}
        self._hooks: dict[str, list[PluginBase]] = {
            "before_fuel_consumption": [],
        }

    def register(self, plugin: PluginBase) -> None:
        self._plugins[plugin.id] = plugin
        self._hooks.setdefault("before_fuel_consumption", []).append(plugin)

    def get(self, plugin_id: str) -> PluginBase | None:
        return self._plugins.get(plugin_id)

    def all_plugins(self) -> list[PluginBase]:
        return list(self._plugins.values())

    def utility_plugins(self) -> list[UtilityPlugin]:
        return [p for p in self._plugins.values() if isinstance(p, UtilityPlugin)]

    def get_hooks(self, hook_name: str) -> list[PluginBase]:
        return self._hooks.get(hook_name, [])

    def load_from_directory(self, plugins_dir: Path) -> list[str]:
        """Загрузить плагины из plugins/*/manifest.json + plugin.py."""
        loaded: list[str] = []
        if not plugins_dir.is_dir():
            return loaded

        for manifest_path in plugins_dir.glob("*/manifest.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                plugin_dir = manifest_path.parent
                entry = manifest.get("entry", "plugin.py")
                module_path = plugin_dir / entry

                if not module_path.exists():
                    continue

                module_name = f"kotel_plugin_{manifest.get('id', plugin_dir.name)}"
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                factory = getattr(module, "create_plugin", None)
                if factory is None:
                    continue

                plugin = factory()
                if isinstance(plugin, PluginBase):
                    self.register(plugin)
                    loaded.append(plugin.id)
            except Exception:
                continue

        return loaded


def create_default_registry(project_root: Path) -> PluginRegistry:
    registry = PluginRegistry()
    plugins_dir = project_root / "plugins"
    registry.load_from_directory(plugins_dir)
    return registry
