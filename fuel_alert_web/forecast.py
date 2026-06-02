from __future__ import annotations

from datetime import datetime, timedelta

from .models import ForecastRow, FuelReading, RtgConfig


def forecast_reading(reading: FuelReading | None, now: datetime, config: RtgConfig) -> ForecastRow:
    if reading is None or reading.last_check is None or reading.level_pct is None:
        equipment = reading.equipment if reading else ""
        return ForecastRow(
            equipment=equipment,
            last_check=reading.last_check if reading else None,
            last_level_pct=reading.level_pct if reading else None,
            current_liters=None,
            current_pct=None,
            time_to_warning=None,
            time_to_stop=None,
            hours_to_warning=None,
            hours_to_stop=None,
            status="NO_DATA",
            checked_by=reading.checked_by if reading else "",
            note="Khong co checklist hop le",
        )

    elapsed_hours = max((now - reading.last_check).total_seconds() / 3600, 0)
    start_liters = reading.level_pct / 100 * config.tank_liters
    current_liters = max(start_liters - elapsed_hours * config.consumption_liters_per_hour, 0)
    current_pct = current_liters / config.tank_liters * 100 if config.tank_liters else 0
    warning_liters = config.warning_threshold_pct / 100 * config.tank_liters
    stop_liters = config.stop_threshold_pct / 100 * config.tank_liters
    hours_to_warning = hours_until_threshold(current_liters, warning_liters, config.consumption_liters_per_hour)
    hours_to_stop = hours_until_threshold(current_liters, stop_liters, config.consumption_liters_per_hour)
    time_to_warning = now + timedelta(hours=hours_to_warning) if hours_to_warning is not None else None
    time_to_stop = now + timedelta(hours=hours_to_stop) if hours_to_stop is not None else None

    if current_pct <= config.stop_threshold_pct:
        status = "CRITICAL"
    elif current_pct <= config.warning_threshold_pct:
        status = "WARNING"
    elif hours_to_warning is not None and hours_to_warning <= config.warning_horizon_hours:
        status = "WARNING"
    else:
        status = "OK"

    return ForecastRow(
        equipment=reading.equipment,
        last_check=reading.last_check,
        last_level_pct=reading.level_pct,
        current_liters=current_liters,
        current_pct=current_pct,
        time_to_warning=time_to_warning,
        time_to_stop=time_to_stop,
        hours_to_warning=hours_to_warning,
        hours_to_stop=hours_to_stop,
        status=status,
        checked_by=reading.checked_by,
    )


def hours_until_threshold(current_liters: float, threshold_liters: float, consumption_liters_per_hour: float) -> float | None:
    if consumption_liters_per_hour <= 0:
        return None
    if current_liters <= threshold_liters:
        return 0.0
    return (current_liters - threshold_liters) / consumption_liters_per_hour


def forecast_all(readings: dict[str, FuelReading], now: datetime, config: RtgConfig) -> list[ForecastRow]:
    rows: list[ForecastRow] = []
    for equipment in config.equipment:
        reading = readings.get(equipment)
        if reading is None:
            reading = FuelReading(equipment=equipment, last_check=None, level_pct=None)
        rows.append(forecast_reading(reading, now, config))
    return rows
