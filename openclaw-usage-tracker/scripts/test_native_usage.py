import copy
import unittest
from decimal import Decimal

from native_usage import AcquisitionError, UsageError, acquire, category, date_bounds, summarize


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


class RefreshGateway(FakeGateway):
    def __init__(self, listings, inventory=(), scoped=None):
        super().__init__(listings[0], list(inventory), scoped)
        self.listings = iter(listings)

    def usage(self, params):
        if "key" not in params:
            self.listing = next(self.listings, self.listing)
        return super().usage(params)


class UsageTests(unittest.TestCase):
    def test_scoped_retries_follow_full_refresh_pass(self):
        rows = [session(str(i), key=f'agent:main:test-{i}') for i in range(20)]

        class ColdGateway(FakeGateway):
            def usage(self, params):
                if 'key' not in params:
                    return super().usage(params)
                self.calls.append(params.copy())
                row = next(r for r in rows if r['key'] == params['key'])
                keys = {c['key'] for c in self.calls if 'key' in c}
                return {'sessions': [copy.deepcopy(row) if len(keys) == len(rows)
                                     else {**row, 'usage': None}], 'totals': {}}

        gateway = ColdGateway({'sessions': [{**r, 'usage': None} for r in rows],
                               'totals': {}}, [])
        result = acquire('2026-09-04', '2026-09-04', 'UTC', gateway)
        self.assertEqual(result['quality']['completeness'], 'complete')
        calls = [c['key'] for c in gateway.calls if 'key' in c]
        self.assertEqual(len(set(calls[:20])), 20)
        self.assertLessEqual(len(calls), 40)

    def test_inventory_only_gaps_do_not_repeat_fresh_listing(self):
        begin, _ = date_bounds('2026-09-04', '2026-09-04', 'UTC')
        row = session()
        gateway = FakeGateway({'sessions': [], 'totals': {}},
            [{**row, 'updatedAt': begin + 1000, 'sessionStartedAt': begin}],
            {'sessions': [row], 'totals': row['usage']})
        result = acquire('2026-09-04', '2026-09-04', 'UTC', gateway)
        self.assertEqual(result['quality']['completeness'], 'complete')
        self.assertEqual(len(gateway.calls), 2)

    def test_batch_refresh_recovers_archives_without_scoped_queries(self):
        rows = [session(str(i)) for i in range(12)]
        totals = summarize(rows, '2026-09-04', '2026-09-04', 'UTC')['total']
        gateway = RefreshGateway([
            {'sessions': [{**r, 'usage': None} for r in rows], 'totals': {}},
            {'sessions': rows, 'totals': totals},
        ])
        result = acquire('2026-09-04', '2026-09-04', 'UTC', gateway)
        self.assertEqual(result['quality']['resolvedBatchSessions'], 12)
        self.assertEqual(result['quality']['completeness'], 'complete')
        self.assertEqual(result['total']['totalTokens'], 12 * 310)
        self.assertEqual(len(gateway.calls), 2)

    def test_refresh_does_not_double_count_known_usage(self):
        row, other = session(), session('b')
        gateway = RefreshGateway([
            {'sessions': [row, {**other, 'usage': None}], 'totals': row['usage']},
            {'sessions': [row, other], 'totals': summarize([row, other],
                '2026-09-04', '2026-09-04', 'UTC')['total']},
        ])
        result = acquire('2026-09-04', '2026-09-04', 'UTC', gateway)
        self.assertEqual(result['total']['totalTokens'], 620)
        self.assertEqual(result['quality']['resolvedBatchSessions'], 1)

    def test_missing_identity_cannot_disappear_during_refresh(self):
        row = session()
        gateway = RefreshGateway([
            {'sessions': [{**row, 'usage': None}], 'totals': {}},
            {'sessions': [], 'totals': {}},
        ], scoped={'sessions': [], 'totals': {}})
        result = acquire('2026-09-04', '2026-09-04', 'UTC', gateway)
        self.assertEqual(result['quality']['completeness'], 'partial')
        self.assertEqual(result['quality']['unresolvedSessions'][0]['reason'],
                         'native session not returned')
        self.assertEqual(len([c for c in gateway.calls if 'key' in c]), 1)

    def test_malformed_refresh_fails_reconciliation(self):
        row = session()
        gateway = RefreshGateway([
            {'sessions': [{**row, 'usage': None}], 'totals': {}},
            {'sessions': [row], 'totals': {}},
        ])
        with self.assertRaises(UsageError):
            acquire('2026-09-04', '2026-09-04', 'UTC', gateway)

    def test_budget_exhaustion_retains_known_usage_and_reason(self):
        row, other = session(), session('b')
        gateway = RefreshGateway([
            {'sessions': [row, {**other, 'usage': None}], 'totals': row['usage']},
            AcquisitionError('native usage acquisition budget exhausted'),
        ], scoped=AcquisitionError('native usage acquisition budget exhausted'))
        result = acquire('2026-09-04', '2026-09-04', 'UTC', gateway)
        self.assertEqual(result['total']['totalTokens'], 310)
        self.assertEqual(result['quality']['completeness'], 'partial')
        self.assertIn('budget exhausted', result['quality']['unresolvedSessions'][0]['reason'])

    def test_batch_refresh_retries_are_bounded(self):
        rows = [{**session(str(i)), 'usage': None} for i in range(6)]
        gateway = RefreshGateway([{'sessions': rows, 'totals': {}}],
                                 scoped={'sessions': [], 'totals': {}})
        result = acquire('2026-09-04', '2026-09-04', 'UTC', gateway)
        self.assertEqual(len([c for c in gateway.calls if 'key' not in c]), 4)
        self.assertEqual(len(result['quality']['unresolvedSessions']), 6)

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
