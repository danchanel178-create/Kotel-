"""Абстракция источников данных для будущих БД."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..core.tables import (
    Q5_NOMINAL_CURVE,
    SLAG_ENTHALPY_TABLE,
    load_q5_curve_from_file,
    slag_enthalpy,
)


class DataProvider(ABC):
    """Интерфейс провайдера справочных данных."""

    @abstractmethod
    def get_fuel_properties(self, fuel_id: str) -> dict[str, Any] | None:
        """Свойства топлива по идентификатору."""

    @abstractmethod
    def get_q5_curve(self) -> list[tuple[float, float]]:
        """Кривая q₅ном (рис. 5.1)."""

    @abstractmethod
    def get_slag_enthalpy(self, t_shl: float) -> float | None:
        """(cθ)_шл по температуре."""

    @abstractmethod
    def list_fuels(self) -> list[dict[str, str]]:
        """Список доступных видов топлива."""


class JsonFileDataProvider(DataProvider):
    """Провайдер на основе локальных JSON-файлов."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._fuels_path = data_dir / "fuels.json"
        self._q5_path = data_dir / "q5_nominal.json"
        self._fuels: dict[str, Any] | None = None

    def _load_fuels(self) -> dict[str, Any]:
        if self._fuels is None:
            if self._fuels_path.exists():
                self._fuels = json.loads(self._fuels_path.read_text(encoding="utf-8"))
            else:
                self._fuels = {"fuels": []}
        return self._fuels

    def get_fuel_properties(self, fuel_id: str) -> dict[str, Any] | None:
        for fuel in self._load_fuels().get("fuels", []):
            if fuel.get("id") == fuel_id:
                return fuel
        return None

    def get_q5_curve(self) -> list[tuple[float, float]]:
        if self._q5_path.exists():
            return load_q5_curve_from_file(self._q5_path)
        return Q5_NOMINAL_CURVE

    def get_slag_enthalpy(self, t_shl: float) -> float | None:
        return slag_enthalpy(t_shl, SLAG_ENTHALPY_TABLE)

    def list_fuels(self) -> list[dict[str, str]]:
        return [
            {"id": f["id"], "name": f.get("name", f["id"])}
            for f in self._load_fuels().get("fuels", [])
        ]


class InMemoryDataProvider(DataProvider):
    """Встроенный провайдер по умолчанию."""

    def get_fuel_properties(self, fuel_id: str) -> dict[str, Any] | None:
        return None

    def get_q5_curve(self) -> list[tuple[float, float]]:
        return Q5_NOMINAL_CURVE

    def get_slag_enthalpy(self, t_shl: float) -> float | None:
        return slag_enthalpy(t_shl)

    def list_fuels(self) -> list[dict[str, str]]:
        return []


class DatabaseDataProvider(DataProvider):
    """
    Заглушка для будущего подключения к БД.
    Реализуйте connect() и запросы под вашу СУБД.
    """

    def __init__(self, connection_string: str) -> None:
        self._conn_str = connection_string
        self._connected = False

    def connect(self) -> None:
        # TODO: подключение к PostgreSQL / SQLite / др.
        self._connected = True

    def get_fuel_properties(self, fuel_id: str) -> dict[str, Any] | None:
        if not self._connected:
            return None
        return None

    def get_q5_curve(self) -> list[tuple[float, float]]:
        return Q5_NOMINAL_CURVE

    def get_slag_enthalpy(self, t_shl: float) -> float | None:
        return slag_enthalpy(t_shl)

    def list_fuels(self) -> list[dict[str, str]]:
        return []
