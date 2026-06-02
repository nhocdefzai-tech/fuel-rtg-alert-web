from __future__ import annotations

import unittest
from datetime import datetime

from fuel_alert_web.models import RtgMapping
from fuel_alert_web.planner import select_active_mappings


class PlannerTest(unittest.TestCase):
    def test_active_vessel_window_beats_finished_buffer_window(self):
        now = datetime(2026, 6, 2, 16, 13)
        mappings = [
            RtgMapping(
                rtg="RTG 01",
                visit_code="NBT2622S",
                active_from=datetime(2026, 6, 2, 5, 0),
                active_to=datetime(2026, 6, 2, 14, 30),
                priority_weight=9,
            ),
            RtgMapping(
                rtg="RTG 01",
                visit_code="ZMS7W",
                active_from=datetime(2026, 6, 2, 9, 0),
                active_to=datetime(2026, 6, 3, 5, 30),
                priority_weight=9,
            ),
        ]

        selected = select_active_mappings(mappings, now, buffer_hours=2)

        self.assertEqual("ZMS7W", selected["RTG 01"].visit_code)

    def test_finished_vessel_still_counts_during_buffer_when_no_active_vessel(self):
        now = datetime(2026, 6, 2, 15, 0)
        mappings = [
            RtgMapping(
                rtg="RTG 02",
                visit_code="NBT2622S",
                active_from=datetime(2026, 6, 2, 5, 0),
                active_to=datetime(2026, 6, 2, 14, 30),
                priority_weight=9,
            )
        ]

        selected = select_active_mappings(mappings, now, buffer_hours=2)

        self.assertEqual("NBT2622S", selected["RTG 02"].visit_code)


if __name__ == "__main__":
    unittest.main()
