import datetime as dt
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('report', Path(__file__).with_name('daily-cost-report.py'))
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class CalendarTests(unittest.TestCase):
    def test_monday_uses_completed_previous_week(self):
        self.assertEqual(report.previous_week(dt.date(2026, 9, 7)), ('2026-08-31', '2026-09-06'))

    def test_midweek_does_not_include_current_partial_week(self):
        self.assertEqual(report.previous_week(dt.date(2026, 9, 5)), ('2026-08-24', '2026-08-30'))

    def test_year_boundary(self):
        self.assertEqual(report.previous_week(dt.date(2026, 1, 1)), ('2025-12-22', '2025-12-28'))


if __name__ == '__main__':
    unittest.main()
