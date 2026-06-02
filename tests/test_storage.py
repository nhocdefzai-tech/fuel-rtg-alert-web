from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fuel_alert_web.storage import Storage


class StorageTest(unittest.TestCase):
    def test_create_update_schedule_and_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "fuel.db")
            schedule_id = storage.create_schedule()
            updated = storage.update_schedule(
                schedule_id,
                {
                    "vessel_name": "UMM SALAL",
                    "visit_code": "usl614w",
                    "etb": "2026-06-02T18:00",
                    "etd": "2026-06-03T06:00",
                    "priority": 1,
                    "rtgs": ["rtg 1", "RTG 08"],
                },
            )
            self.assertEqual("USL614W", updated["visit_code"])
            self.assertEqual(["RTG 01", "RTG 08"], updated["rtgs"])
            schedules, mappings = storage.schedules_and_mappings()
            self.assertEqual(1, len(schedules))
            self.assertEqual(2, len(mappings))

    def test_sources_are_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "fuel.db")
            path = Path(tmp) / "fuel.xlsx"
            storage.set_source("fuel", path)
            self.assertEqual(path, storage.get_source("fuel"))


if __name__ == "__main__":
    unittest.main()
