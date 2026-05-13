from __future__ import annotations

from typing import Any

from polyforge.ir.nodes import Quantity


def explicit_unknown() -> dict[str, Any]:
    return {"value": None, "explicit_unknown": True}


def normalize_unknown(value: Any) -> Any:
    return explicit_unknown() if value == "unknown" else value


def numeric_value(value: Any) -> float | int | None:
    if isinstance(value, Quantity):
        value = value.value
    if isinstance(value, int | float):
        return value
    return None


def normalize_molar_mass(value: Quantity | None) -> float | None:
    if value is None:
        return None
    if value.unit not in (None, "g/mol"):
        raise ValueError(f"unsupported molar mass unit: {value.unit}")
    return float(value.value)


def normalize_temperature(value: Quantity) -> float:
    if value.unit not in (None, "K"):
        raise ValueError(f"unsupported temperature unit: {value.unit}")
    return float(value.value)


def normalize_pressure(value: Quantity) -> float:
    if value.unit in (None, "Pa"):
        return float(value.value)
    if value.unit == "atm":
        return float(value.value) * 101325.0
    raise ValueError(f"unsupported pressure unit: {value.unit}")


def normalize_heating_rate(value: Quantity) -> float:
    if value.unit not in (None, "K/min"):
        raise ValueError(f"unsupported heating-rate unit: {value.unit}")
    return float(value.value)


def normalize_measurement_field(key: str, value: Any) -> tuple[str, Any]:
    if key == "heating_rate" and isinstance(value, Quantity):
        return "heating_rate_K_per_min", normalize_heating_rate(value)
    if key == "pressure" and isinstance(value, Quantity):
        return "pressure_Pa", normalize_pressure(value)
    if key == "temperature" and isinstance(value, Quantity):
        return "temperature_K", normalize_temperature(value)
    if isinstance(value, Quantity):
        return key, value.value if value.unit is None else f"{value.value} {value.unit}"
    return key, normalize_unknown(value)
