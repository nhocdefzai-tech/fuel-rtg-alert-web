from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fuel_alert_web.web import create_app


class WebTest(unittest.TestCase):
    def test_state_and_schedule_autosave(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            app.testing = True
            client = app.test_client()
            created = client.post("/api/schedules")
            self.assertEqual(200, created.status_code)
            schedule_id = created.get_json()["schedule"]["id"]
            saved = client.put(
                f"/api/schedules/{schedule_id}",
                json={
                    "vessel_name": "TEST VESSEL",
                    "etb": "2026-06-02T18:00",
                    "etd": "2026-06-03T06:00",
                    "rtgs": ["RTG 01"],
                },
            )
            self.assertEqual(200, saved.status_code)
            state = client.get("/api/state").get_json()
            self.assertEqual(1, len(state["schedules"]))
            self.assertEqual(["RTG 01"], state["schedules"][0]["rtgs"])


if __name__ == "__main__":
    unittest.main()
