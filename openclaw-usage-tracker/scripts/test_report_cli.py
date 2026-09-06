import datetime as dt
import importlib.util
from pathlib import Path
import unittest
import contextlib
import io
import json
from unittest.mock import patch

from native_usage import UsageError, summarize
from test_native_usage import session

spec = importlib.util.spec_from_file_location('report', Path(__file__).with_name('daily-cost-report.py'))
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class CalendarTests(unittest.TestCase):
    def invoke(self, responses, format='json'):
        output = io.StringIO()
        with patch.object(report, 'acquire', side_effect=responses), patch.object(
                report.sys, 'argv', ['report', '2026-09-04', '--trend-days', '7',
                                    '--format', format]), contextlib.redirect_stdout(output):
            code = report.main()
        return code, output.getvalue()

    def test_unavailable_trend_keeps_valid_daily_json(self):
        daily = summarize([session()], '2026-09-04', '2026-09-04', 'UTC')
        code, output = self.invoke([daily, UsageError('native usage acquisition budget exhausted')])
        result = json.loads(output)
        self.assertEqual(code, 2)
        self.assertEqual(result['total']['tokens'], 310)
        self.assertEqual(result['quality']['completeness'], 'complete')
        self.assertEqual(result['trend']['quality']['completeness'], 'unavailable')
        self.assertNotIn('total', result['trend'])

    def test_unavailable_trend_keeps_deliverable_daily_text(self):
        daily = summarize([session()], '2026-09-04', '2026-09-04', 'UTC')
        code, output = self.invoke([daily, UsageError('native usage CLI failed')], 'discord')
        self.assertEqual(code, 2)
        self.assertTrue(output.startswith('## 💰'))
        self.assertIn('趋势统计不可用', output)
        self.assertIn('310', output)

    def test_trend_price_gap_is_visible(self):
        daily = summarize([session()], '2026-09-04', '2026-09-04', 'UTC')
        trend = summarize([session()], '2026-08-29', '2026-09-04', 'UTC')
        trend['quality'].update(pricingCompleteness='partial', missingCostEntries=2)
        code, output = self.invoke([daily, trend], 'discord')
        self.assertEqual(code, 2)
        self.assertIn('趋势价格不完整', output)
        self.assertIn('2 条', output)

    def test_monday_uses_completed_previous_week(self):
        self.assertEqual(report.previous_week(dt.date(2026, 9, 7)), ('2026-08-31', '2026-09-06'))

    def test_midweek_does_not_include_current_partial_week(self):
        self.assertEqual(report.previous_week(dt.date(2026, 9, 5)), ('2026-08-24', '2026-08-30'))

    def test_year_boundary(self):
        self.assertEqual(report.previous_week(dt.date(2026, 1, 1)), ('2025-12-22', '2025-12-28'))


if __name__ == '__main__':
    unittest.main()
