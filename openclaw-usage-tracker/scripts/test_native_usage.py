import copy
import unittest
from decimal import Decimal

from native_usage import UsageError, acquire, category, date_bounds, summarize


def session(sid="a", cost="0.15", key="agent:main:cron:test"):
    totals = dict(input=100, output=10, cacheRead=200, cacheWrite=0,
                  totalTokens=310, totalCost=Decimal(cost), missingCostEntries=0)
    return dict(agentId="main", sessionId=sid, key=key, usage={
        **totals, "modelUsage": [dict(provider="proxy", model="test-model", count=2, totals=totals.copy())],
        "dailyBreakdown": [dict(date="2026-09-04", tokens=310, cost=Decimal(cost))],
        "dailyModelUsage": [dict(date="2026-09-04", provider="proxy", model="test-model", count=2)]})


class FakeGateway:
    def __init__(self, listing, inventory, scoped=None):
        self.listing, self.inventory, self.scoped = listing, inventory, scoped
        self.calls = []

    def command(self, args):
        return {"sessions": self.inventory, "hasMore": False}

    def usage(self, params):
        self.calls.append(params.copy())
        result = self.scoped if "key" in params else self.listing
        if isinstance(result, Exception):
            raise result
        return copy.deepcopy(result)


class UsageTests(unittest.TestCase):
    def test_aggregate_exact_decimals_and_unknown_category(self):
        a, b = session(), session("b", "0.2", "agent:main:opaque")
        result = summarize([a, b], "2026-09-04", "2026-09-04", "Asia/Shanghai")
        self.assertEqual(result["total"]["totalCost"], Decimal("0.35"))
        self.assertEqual(result["total"]["totalTokens"], 620)
        self.assertEqual(result["categories"]["unknown"]["totalTokens"], 310)
        self.assertEqual(result["total"]["count"], 4)

    def test_duplicate_native_instance_is_rejected(self):
        with self.assertRaises(UsageError):
            summarize([session(), session()], "2026-09-04", "2026-09-04", "UTC")

    def test_model_and_daily_coverage_must_close(self):
        for mutate in (lambda u: u["modelUsage"].clear(), lambda u: u["dailyBreakdown"].clear()):
            row = session()
            mutate(row["usage"])
            with self.assertRaises(UsageError):
                summarize([row], "2026-09-04", "2026-09-04", "UTC")

    def test_zero_mirror_does_not_inflate_call_count(self):
        row = session()
        row["usage"]["modelUsage"].append(dict(provider="openclaw", model="delivery-mirror", count=42, totals={}))
        result = summarize([row], "2026-09-04", "2026-09-04", "UTC")
        self.assertEqual(result["total"]["count"], 2)
        self.assertNotIn(("openclaw", "delivery-mirror"), result["models"])

    def test_nonzero_mirror_is_not_silently_discarded(self):
        row = session()
        row["usage"]["modelUsage"][0]["model"] = "delivery-mirror"
        with self.assertRaises(UsageError):
            summarize([row], "2026-09-04", "2026-09-04", "UTC")

    def test_missing_price_is_separate_from_token_completeness(self):
        row = session(cost="0")
        row["usage"]["missingCostEntries"] = 2
        row["usage"]["modelUsage"][0]["totals"]["missingCostEntries"] = 2
        result = summarize([row], "2026-09-04", "2026-09-04", "UTC")
        self.assertEqual(result["quality"]["completeness"], "complete")
        self.assertEqual(result["quality"]["pricingCompleteness"], "partial")

    def test_scoped_native_query_repairs_missing_list_entry(self):
        row = session()
        gateway = FakeGateway({"sessions": [{**row, "usage": None}], "totals": {}}, [],
                              {"sessions": [row], "totals": row["usage"]})
        result = acquire("2026-09-04", "2026-09-04", "Asia/Shanghai", gateway)
        self.assertEqual(result["total"]["totalTokens"], 310)
        self.assertEqual(result["quality"]["completeness"], "complete")
        self.assertEqual(result["quality"]["resolvedScopedSessions"], 1)

    def test_missing_same_key_but_wrong_generation_is_not_accepted(self):
        row = session()
        gateway = FakeGateway({"sessions": [{**row, "usage": None}], "totals": {}}, [],
                              {"sessions": [session("new-generation")], "totals": {}})
        result = acquire("2026-09-04", "2026-09-04", "Asia/Shanghai", gateway)
        self.assertEqual(result["quality"]["completeness"], "partial")
        self.assertEqual(result["total"]["totalTokens"], 0)

    def test_cross_day_inventory_is_not_ignored_by_updated_at(self):
        begin, finish = date_bounds("2026-09-04", "2026-09-04", "Asia/Shanghai")
        row = session()
        inventory = [{**row, "updatedAt": finish + 1000, "sessionStartedAt": begin - 1000}]
        gateway = FakeGateway({"sessions": [], "totals": {}}, inventory,
                              {"sessions": [row], "totals": row["usage"]})
        result = acquire("2026-09-04", "2026-09-04", "Asia/Shanghai", gateway)
        self.assertEqual(result["total"]["totalTokens"], 310)

    def test_after_date_inventory_is_provably_out_of_scope(self):
        _, finish = date_bounds("2026-09-04", "2026-09-04", "Asia/Shanghai")
        inventory = [{**session(), "updatedAt": finish + 2000, "sessionStartedAt": finish + 1000}]
        gateway = FakeGateway({"sessions": [], "totals": {}}, inventory)
        result = acquire("2026-09-04", "2026-09-04", "Asia/Shanghai", gateway)
        self.assertEqual(result["total"]["totalTokens"], 0)
        self.assertEqual(result["quality"]["completeness"], "complete")

    def test_truncated_totals_fail_closed(self):
        row = session()
        gateway = FakeGateway({"sessions": [], "totals": row["usage"]}, [])
        with self.assertRaises(UsageError):
            acquire("2026-09-04", "2026-09-04", "Asia/Shanghai", gateway)

    def test_full_calendar_range_includes_zero_days(self):
        result = summarize([session()], "2026-09-03", "2026-09-05", "Asia/Shanghai")
        self.assertEqual(len(result["daily"]), 3)
        self.assertEqual(result["daily"]["2026-09-03"]["tokens"], 0)

    def test_timezone_and_date_validation(self):
        self.assertEqual(date_bounds("2026-09-04", "2026-09-04", "Asia/Shanghai")[0], 1788451200000)
        with self.assertRaises(UsageError):
            date_bounds("2026-09-05", "2026-09-04", "UTC")
        self.assertEqual(category(session(key="agent:main:heartbeat:x")), "heartbeat")


if __name__ == "__main__":
    unittest.main()
