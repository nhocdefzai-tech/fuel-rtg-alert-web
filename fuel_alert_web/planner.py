from __future__ import annotations

import math
from datetime import datetime, timedelta

from .models import ForecastRow, RefuelPlanRow, RtgConfig, RtgMapping, VesselSchedule


def build_refuel_plan(
    forecast_rows: list[ForecastRow],
    schedules: list[VesselSchedule],
    mappings: list[RtgMapping],
    workload_by_visit: dict[str, int],
    now: datetime,
    config: RtgConfig,
) -> list[RefuelPlanRow]:
    schedule_by_visit = {item.visit_code: item for item in schedules}
    active_mapping_by_rtg = select_active_mappings(mappings, now, config.vessel_buffer_hours)
    sortable: list[tuple[tuple[float, ...], RefuelPlanRow]] = []

    for row in forecast_rows:
        liters_to_full = None
        if row.status != "NO_DATA" and row.current_liters is not None:
            liters_to_full = round_up(max(config.tank_liters - row.current_liters, 0), config.refuel_round_liters)

        mapping = active_mapping_by_rtg.get(row.equipment)
        visit = mapping.visit_code if mapping else ""
        schedule = schedule_by_visit.get(visit)
        workload = workload_by_visit.get(visit, 0)
        plan_row = RefuelPlanRow(
            rank=0,
            equipment=row.equipment,
            status=row.status,
            current_pct=row.current_pct,
            current_liters=row.current_liters,
            liters_to_full=liters_to_full,
            time_to_stop=row.time_to_stop,
            linked_visit=visit,
            vessel_name=schedule.vessel_name if schedule else "",
            etb=schedule.etb if schedule else None,
            etd=schedule.etd if schedule else None,
            workload_containers=workload,
            reason=make_reason(row, schedule, workload),
        )
        sortable.append((priority_key(row, schedule, workload, now), plan_row))

    ranked: list[RefuelPlanRow] = []
    for rank, (_, row) in enumerate(sorted(sortable, key=lambda item: item[0]), start=1):
        ranked.append(
            RefuelPlanRow(
                rank=rank,
                equipment=row.equipment,
                status=row.status,
                current_pct=row.current_pct,
                current_liters=row.current_liters,
                liters_to_full=row.liters_to_full,
                time_to_stop=row.time_to_stop,
                linked_visit=row.linked_visit,
                vessel_name=row.vessel_name,
                etb=row.etb,
                etd=row.etd,
                workload_containers=row.workload_containers,
                reason=row.reason,
            )
        )
    return ranked


def select_active_mappings(mappings: list[RtgMapping], now: datetime, buffer_hours: float) -> dict[str, RtgMapping]:
    selected: dict[str, tuple[tuple[float, ...], RtgMapping]] = {}
    buffer = timedelta(hours=buffer_hours)
    for mapping in mappings:
        score = mapping_selection_score(mapping, now, buffer)
        if score is None:
            continue
        current = selected.get(mapping.rtg)
        if current is None or score < current[0]:
            selected[mapping.rtg] = (score, mapping)
    return {rtg: item[1] for rtg, item in selected.items()}


def mapping_selection_score(mapping: RtgMapping, now: datetime, buffer: timedelta) -> tuple[float, ...] | None:
    active_from = mapping.active_from
    active_to = mapping.active_to
    buffered_from = active_from - buffer if active_from else None
    buffered_to = active_to + buffer if active_to else None

    if buffered_from and now < buffered_from:
        return None
    if buffered_to and now > buffered_to:
        return None

    phase_rank = 3
    minutes_from_window = 999999.0
    if active_from and active_to and active_from <= now <= active_to:
        phase_rank = 0
        minutes_from_window = 0.0
    elif active_from and not active_to and now >= active_from:
        phase_rank = 0
        minutes_from_window = 0.0
    elif active_to and not active_from and now <= active_to:
        phase_rank = 0
        minutes_from_window = 0.0
    elif active_from and now < active_from:
        phase_rank = 1
        minutes_from_window = (active_from - now).total_seconds() / 60
    elif active_to and now > active_to:
        phase_rank = 2
        minutes_from_window = (now - active_to).total_seconds() / 60

    etd_sort = active_to.timestamp() if active_to else 9999999999.0
    return (phase_rank, -mapping.priority_weight, minutes_from_window, etd_sort)


def priority_key(row: ForecastRow, schedule: VesselSchedule | None, workload: int, now: datetime) -> tuple[float, ...]:
    status_rank = {"CRITICAL": 0, "WARNING": 1, "OK": 2, "NO_DATA": 3}.get(row.status, 4)
    hours_to_stop = row.hours_to_stop if row.hours_to_stop is not None else 99999
    pct = row.current_pct if row.current_pct is not None else 99999
    vessel_rank = 1
    minutes_to_etb = 999999
    schedule_priority = 9
    if schedule:
        vessel_rank = 0
        schedule_priority = schedule.priority
        if schedule.etb:
            minutes_to_etb = (schedule.etb - now).total_seconds() / 60
            if minutes_to_etb < 0 and schedule.etd and now <= schedule.etd:
                minutes_to_etb = 0
    return (status_rank, hours_to_stop, vessel_rank, schedule_priority, max(minutes_to_etb, 0), -workload, pct)


def round_up(value: float, step: int) -> float:
    if step <= 0:
        return value
    return math.ceil(value / step) * step


def make_reason(row: ForecastRow, schedule: VesselSchedule | None, workload: int) -> str:
    parts: list[str] = []
    if row.status == "CRITICAL":
        parts.append("Duoi nguong 15%")
    elif row.status == "WARNING":
        parts.append("Canh bao 25%/24h")
    elif row.status == "NO_DATA":
        parts.append("Thieu du lieu")
    else:
        parts.append("Theo doi")
    if schedule:
        parts.append(f"Lich tau {schedule.vessel_name or schedule.visit_code}")
    if workload:
        parts.append(f"N4 {workload} cont")
    return "; ".join(parts)
