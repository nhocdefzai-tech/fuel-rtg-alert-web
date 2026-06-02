from __future__ import annotations

import argparse
import sys

from .config import make_settings
from .engine import run_analysis, summarize_counts
from .storage import Storage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fuel RTG Alert Web")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Run analysis from uploaded web sources")
    args = parser.parse_args(argv)
    if args.command == "run":
        return cmd_run()
    return 2


def cmd_run() -> int:
    settings = make_settings()
    storage = Storage(settings.runtime_dir / "fuel_alert.db")
    fuel = storage.get_source("fuel")
    n4 = storage.get_source("n4")
    settings = make_settings(fuel_workbook=fuel, n4_txt=n4)
    schedules, mappings = storage.schedules_and_mappings()
    result = run_analysis(settings, schedules, mappings, write_excel=True)
    print(f"Run at: {result.run_at:%Y-%m-%d %H:%M:%S}")
    print("RTG status:", summarize_counts(result))
    for row in result.plan[:5]:
        pct = "" if row.current_pct is None else f"{row.current_pct:.1f}%"
        print(f"- #{row.rank} {row.equipment} {row.status} {pct} {row.reason}")
    if result.output_path:
        print(f"Dashboard: {result.output_path}")
    return 1 if any(status.status == "ERROR" for status in result.statuses) else 0


if __name__ == "__main__":
    sys.exit(main())
