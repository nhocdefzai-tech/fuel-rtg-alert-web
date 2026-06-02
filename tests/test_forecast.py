from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from fuel_alert_web.forecast import forecast_reading
from fuel_alert_web.models import FuelReading, RtgConfig


class ForecastTest(unittest.TestCase):
    def test_consumes_fuel_by_elapsed_hours(self):
        now = datetime(2026, 6, 2, 12, 0)
        reading = FuelReading("RTG 01", now - timedelta(hours=12), 100)
        row = forecast_reading(reading, now, RtgConfig(["RTG 01"]))
        self.assertAlmostEqual(1800, row.current_liters, places=0)
        self.assertAlmostEqual(90, row.current_pct, places=0)
        self.assertEqual("OK", row.status)

    def test_warning_inside_horizon(self):
        now = datetime(2026, 6, 2, 12, 0)
        reading = FuelReading("RTG 01", now, 30)
        row = forecast_reading(reading, now, RtgConfig(["RTG 01"]))
        self.assertEqual("WARNING", row.status)


if __name__ == "__main__":
    unittest.main()
