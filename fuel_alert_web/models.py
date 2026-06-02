from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RtgConfig:
    equipment: list[str]
    tank_liters: float = 2000
    consumption_liters_per_hour: float = 16.6667
    stop_threshold_pct: float = 15
    warning_threshold_pct: float = 25
    warning_horizon_hours: float = 24
    refuel_round_liters: int = 10
    vessel_buffer_hours: float = 2


@dataclass(frozen=True)
class Settings:
    project_root: Path
    fuel_workbook: Path | None
    n4_txt: Path | None
    dashboard_output: Path
    runtime_dir: Path
    checklist_sheet: str
    rtg: RtgConfig


@dataclass(frozen=True)
class FuelReading:
    equipment: str
    last_check: datetime | None
    level_pct: float | None
    checked_by: str = ""


@dataclass(frozen=True)
class ForecastRow:
    equipment: str
    last_check: datetime | None
    last_level_pct: float | None
    current_liters: float | None
    current_pct: float | None
    time_to_warning: datetime | None
    time_to_stop: datetime | None
    hours_to_warning: float | None
    hours_to_stop: float | None
    status: str
    checked_by: str = ""
    note: str = ""


@dataclass(frozen=True)
class VesselSchedule:
    visit_code: str
    vessel_name: str
    etb: datetime | None
    etd: datetime | None
    berth_area: str = ""
    priority: int = 3
    notes: str = ""


@dataclass(frozen=True)
class RtgMapping:
    rtg: str
    visit_code: str = ""
    active_from: datetime | None = None
    active_to: datetime | None = None
    priority_weight: float = 1.0


@dataclass(frozen=True)
class N4WorkloadRow:
    visit_code: str
    vessel_name: str
    service: str
    transit: str
    current_position: str
    container_count: int


@dataclass(frozen=True)
class RefuelPlanRow:
    rank: int
    equipment: str
    status: str
    current_pct: float | None
    current_liters: float | None
    liters_to_full: float | None
    time_to_stop: datetime | None
    linked_visit: str = ""
    vessel_name: str = ""
    etb: datetime | None = None
    etd: datetime | None = None
    workload_containers: int = 0
    reason: str = ""


@dataclass(frozen=True)
class SourceStatus:
    source: str
    path: Path | None
    exists: bool
    rows: int = 0
    last_modified: datetime | None = None
    status: str = "OK"
    message: str = ""


@dataclass(frozen=True)
class RunResult:
    run_at: datetime
    forecasts: list[ForecastRow]
    plan: list[RefuelPlanRow]
    workload: list[N4WorkloadRow]
    statuses: list[SourceStatus]
    warnings: list[str]
    output_path: Path | None = None
