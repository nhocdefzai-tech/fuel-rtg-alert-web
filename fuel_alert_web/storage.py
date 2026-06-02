from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import RtgMapping, VesselSchedule
from .utils import clean_visit, normalize_rtg_name, parse_datetime


class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS vessel_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    active INTEGER NOT NULL DEFAULT 1,
                    vessel_name TEXT NOT NULL DEFAULT '',
                    visit_code TEXT NOT NULL DEFAULT '',
                    etb TEXT NOT NULL DEFAULT '',
                    etd TEXT NOT NULL DEFAULT '',
                    berth_area TEXT NOT NULL DEFAULT '',
                    priority INTEGER NOT NULL DEFAULT 3,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS vessel_rtgs (
                    schedule_id INTEGER NOT NULL,
                    rtg TEXT NOT NULL,
                    PRIMARY KEY (schedule_id, rtg),
                    FOREIGN KEY (schedule_id) REFERENCES vessel_schedules(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS uploaded_sources (
                    kind TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL
                );
                """
            )

    def set_source(self, kind: str, path: Path) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO uploaded_sources(kind, path, uploaded_at)
                VALUES (?, ?, ?)
                ON CONFLICT(kind) DO UPDATE SET path=excluded.path, uploaded_at=excluded.uploaded_at
                """,
                (kind, str(path), now),
            )

    def get_source(self, kind: str) -> Path | None:
        with self.connect() as conn:
            row = conn.execute("SELECT path FROM uploaded_sources WHERE kind = ?", (kind,)).fetchone()
        return Path(row["path"]) if row else None

    def list_sources(self) -> dict[str, str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT kind, path FROM uploaded_sources").fetchall()
        return {row["kind"]: row["path"] for row in rows}

    def create_schedule(self) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO vessel_schedules(active, vessel_name, visit_code, etb, etd, berth_area, priority, notes, created_at, updated_at)
                VALUES (1, '', '', '', '', '', 3, '', ?, ?)
                """,
                (now, now),
            )
            return int(cursor.lastrowid)

    def update_schedule(self, schedule_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {"active", "vessel_name", "visit_code", "etb", "etd", "berth_area", "priority", "notes"}
        fields: list[str] = []
        values: list[Any] = []
        for key in allowed:
            if key not in payload:
                continue
            value = payload[key]
            if key == "active":
                value = 1 if bool(value) else 0
            elif key == "visit_code":
                value = clean_visit(value)
            elif key == "priority":
                value = int(value or 3)
            else:
                value = str(value or "")
            fields.append(f"{key} = ?")
            values.append(value)
        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat(timespec="seconds"))
        values.append(schedule_id)
        with self.connect() as conn:
            conn.execute(f"UPDATE vessel_schedules SET {', '.join(fields)} WHERE id = ?", values)
            if "rtgs" in payload:
                conn.execute("DELETE FROM vessel_rtgs WHERE schedule_id = ?", (schedule_id,))
                for rtg in payload["rtgs"] or []:
                    name = normalize_rtg_name(rtg)
                    if name:
                        conn.execute("INSERT OR IGNORE INTO vessel_rtgs(schedule_id, rtg) VALUES (?, ?)", (schedule_id, name))
        return self.get_schedule(schedule_id)

    def delete_schedule(self, schedule_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM vessel_rtgs WHERE schedule_id = ?", (schedule_id,))
            conn.execute("DELETE FROM vessel_schedules WHERE id = ?", (schedule_id,))

    def get_schedule(self, schedule_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM vessel_schedules WHERE id = ?", (schedule_id,)).fetchone()
            rtgs = [item["rtg"] for item in conn.execute("SELECT rtg FROM vessel_rtgs WHERE schedule_id = ? ORDER BY rtg", (schedule_id,))]
        if row is None:
            raise KeyError(schedule_id)
        return row_to_dict(row, rtgs)

    def list_schedule_dicts(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM vessel_schedules ORDER BY active DESC, etb ASC, id ASC").fetchall()
            rtg_rows = conn.execute("SELECT schedule_id, rtg FROM vessel_rtgs ORDER BY rtg").fetchall()
        rtgs_by_id: dict[int, list[str]] = {}
        for row in rtg_rows:
            rtgs_by_id.setdefault(int(row["schedule_id"]), []).append(row["rtg"])
        return [row_to_dict(row, rtgs_by_id.get(int(row["id"]), [])) for row in rows]

    def schedules_and_mappings(self) -> tuple[list[VesselSchedule], list[RtgMapping]]:
        schedules: list[VesselSchedule] = []
        mappings: list[RtgMapping] = []
        for item in self.list_schedule_dicts():
            if not item["active"]:
                continue
            visit_code = effective_visit_code(item)
            schedule = VesselSchedule(
                visit_code=visit_code,
                vessel_name=item["vessel_name"],
                etb=parse_datetime(item["etb"]),
                etd=parse_datetime(item["etd"]),
                berth_area=item["berth_area"],
                priority=int(item["priority"] or 3),
                notes=item["notes"],
            )
            schedules.append(schedule)
            for rtg in item["rtgs"]:
                mappings.append(
                    RtgMapping(
                        rtg=rtg,
                        visit_code=visit_code,
                        active_from=schedule.etb,
                        active_to=schedule.etd,
                        priority_weight=max(1, 10 - schedule.priority),
                    )
                )
        return schedules, mappings


def effective_visit_code(item: dict[str, Any]) -> str:
    visit_code = clean_visit(item.get("visit_code"))
    return visit_code or f"WEB-{item['id']}"


def row_to_dict(row: sqlite3.Row, rtgs: list[str]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "active": bool(row["active"]),
        "vessel_name": row["vessel_name"],
        "visit_code": row["visit_code"],
        "etb": row["etb"],
        "etd": row["etd"],
        "berth_area": row["berth_area"],
        "priority": int(row["priority"]),
        "notes": row["notes"],
        "rtgs": rtgs,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
