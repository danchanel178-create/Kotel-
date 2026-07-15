"""Базовые классы плагинов и утилит."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class PluginBase(ABC):
    """
    Базовый класс сторонней утилиты.
    Плагин может быть отдельным окном, расчётным модулем или источником данных.
    """

    id: ClassVar[str] = "base"
    name: ClassVar[str] = "Базовый плагин"
    version: ClassVar[str] = "0.0.0"
    description: ClassVar[str] = ""

    @abstractmethod
    def activate(self, host: Any) -> None:
        """Вызывается при активации плагина (открытие окна, регистрация хуков)."""

    def on_before_fuel_consumption(self, context: dict[str, Any]) -> None:
        """Хук перед расчётом расхода топлива (5-17–5-24)."""

    def get_menu_label(self) -> str:
        return self.name


class UtilityPlugin(PluginBase):
    """Утилита с собственным UI (например, расчёт качества пара)."""

    @abstractmethod
    def open_window(self, parent: Any) -> None:
        """Открыть окно утилиты."""


class CalculationPlugin(PluginBase):
    """Расчётный модуль без UI — встраивается в цепочку расчёта."""

    @abstractmethod
    def calculate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Выполнить расчёт и вернуть результаты."""
