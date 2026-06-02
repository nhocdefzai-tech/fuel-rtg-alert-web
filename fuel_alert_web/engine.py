from __future__ import annotations

from datetime import datetime

from .exporter import export_dashboard
from .forecast import forecast_all
from .ingest import read_fuel_readings, read_n4_workload, workload_by_visit
from .models import RtgMapping, RunResult, Settings, SourceStatus, VesselSchedule
from .planner import build_refuel_plan


def run_analysis(
    settings: Settings,
    schedules: list[VesselSchedule],
    mappings: list[RtgMapping],
    write_excel: bool = False,
) -> RunResult:
    run_at = datetime.now().replace(microsecond=0)
    warnings: list[str] = []
    statuses: list[SourceStatus] = []

    readings, fuel_status, fuel_warnings = read_fuel_readings(settings.fuel_workbook, settings.checklist_sheet, settings.rtg.equipment)
    statuses.append(fuel_status)
    warnings.extend(fuel_warnings)

    workload, n4_status, n4_warnings = read_n4_workload(settings.n4_txt)
    statuses.append(n4_status)
    warnings.extend(n4_warnings)

    forecasts = forecast_all(readings, run_at, settings.rtg)
    plan = build_refuel_plan(forecasts, schedules, mappings, workload_by_visit(workload), run_at, settings.rtg)
    output = None
    if write_excel:
        output = export_dashboard(settings.dashboard_output, run_at, forecasts, plan, workload, statuses, warnings)

    return RunResult(
        run_at=run_at,
        forecasts=forecasts,
        plan=plan,
        workload=workload,
        statuses=statuses,
        warnings=warnings,
        output_path=output,
    )


def summarize_counts(result: RunResult) -> dict[str, int]:
    counts = {"CRITICAL": 0, "WARNING": 0, "OK": 0, "NO_DATA": 0}
    for row in result.forecasts:
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts
