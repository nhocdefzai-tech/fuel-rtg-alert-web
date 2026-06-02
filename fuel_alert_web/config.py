from __future__ import annotations

from pathlib import Path

from .models import RtgConfig, Settings


DEFAULT_EQUIPMENT = [f"RTG {index:02d}" for index in range(1, 16)]


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def make_settings(
    project_root: Path | None = None,
    fuel_workbook: Path | None = None,
    n4_txt: Path | None = None,
    dashboard_output: Path | None = None,
) -> Settings:
    root = (project_root or default_project_root()).resolve()
    runtime = root / "runtime"
    return Settings(
        project_root=root,
        fuel_workbook=fuel_workbook,
        n4_txt=n4_txt,
        dashboard_output=dashboard_output or runtime / "outputs" / "fuel_dashboard.xlsx",
        runtime_dir=runtime,
        checklist_sheet="Linked_data",
        rtg=RtgConfig(equipment=DEFAULT_EQUIPMENT),
    )
