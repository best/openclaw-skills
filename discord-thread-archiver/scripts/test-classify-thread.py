#!/usr/bin/env python3
"""Regression tests for classify-thread.py."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).with_name("classify-thread.py")
SPEC = importlib.util.spec_from_file_location("classify_thread", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CLASSIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLASSIFIER)


def message(message_id: int, content: str, is_bot: bool) -> dict[str, object]:
    return {"messageId": str(message_id), "content": content, "isBot": is_bot}


def facts(messages: list[dict[str, object]], **overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "name": "Example service maintenance",
        "pinned": False,
        "lastMessageAgeMinutes": 226,
        "messageOrder": "oldest_to_newest",
        "historyScanComplete": True,
        "humanInitiated": True,
        "hadHistoricalHumanParticipation": True,
        "messages": messages,
        "operationalThreadPrefixes": ["🤖 "],
    }
    result.update(overrides)
    return result


class ClassifierTests(unittest.TestCase):
    def test_old_closure_cannot_close_new_human_request(self) -> None:
        messages = [message(1, 'done', False), message(2, 'Please add export support', False)]
        for age in (10, 3000):
            with self.subTest(age=age):
                result = CLASSIFIER.classify(facts(messages, lastMessageAgeMinutes=age))
                self.assertEqual(result['verdict'], 'keep')

    def test_old_closure_cannot_bypass_new_exchange_idle_gate(self) -> None:
        messages = [message(1, 'done', False), message(2, 'Add export support', False),
                    message(3, 'Here is the implementation.', True)]
        result = CLASSIFIER.classify(facts(messages, lastMessageAgeMinutes=10))
        self.assertEqual(result['verdict'], 'keep')
        result = CLASSIFIER.classify(facts(messages, lastMessageAgeMinutes=90))
        self.assertEqual(result['reasonCode'], 'collab_answered_idle')

    def test_operational_question_cannot_be_closed_by_old_done(self) -> None:
        result = CLASSIFIER.classify(facts(
            [message(1, 'completed', True), message(2, 'Continue?', True)],
            name='🤖 maintenance', humanInitiated=False, hadHistoricalHumanParticipation=False))
        self.assertEqual(result['verdict'], 'keep')

    def test_historical_human_outside_window_archives_idle_final(self) -> None:
        messages = [message(index, "tool progress", True) for index in range(101, 126)]
        messages.append(message(126, "Maintenance completed; example service checks passed.", True))
        result = CLASSIFIER.classify(facts(messages))
        self.assertEqual((result["verdict"], result["reasonCode"]), ("archive", "collab_answered_idle"))

    def test_historical_human_prevents_operational_classification(self) -> None:
        messages = [message(201, "tool output", True), message(202, "completed successfully", True)]
        result = CLASSIFIER.classify(facts(messages, name="🤖 upgrade"))
        self.assertEqual((result["threadType"], result["reasonCode"]), ("normal", "collab_answered_idle"))

    def test_incomplete_history_is_kept(self) -> None:
        result = CLASSIFIER.classify(facts(
            [message(301, "completed", True)],
            historyScanComplete=False,
            humanInitiated=False,
            hadHistoricalHumanParticipation=False,
        ))
        self.assertEqual((result["verdict"], result["reasonCode"]), ("keep", "facts_incomplete"))

    def test_duplicate_ids_are_invalid(self) -> None:
        result = CLASSIFIER.classify(facts([
            message(401, "request", False),
            message(401, "done", True),
        ]))
        self.assertEqual((result["verdict"], result["reasonCode"]), ("keep", "facts_invalid"))

    def test_wrong_order_is_invalid(self) -> None:
        result = CLASSIFIER.classify(facts([
            message(502, "done", True),
            message(501, "request", False),
        ]))
        self.assertEqual((result["verdict"], result["reasonCode"]), ("keep", "facts_invalid"))

    def test_later_bot_question_overrides_old_closure(self) -> None:
        result = CLASSIFIER.classify(facts([
            message(601, "完成了", False),
            message(602, "还需要我继续吗？", True),
        ]))
        self.assertEqual((result["verdict"], result["reasonCode"]), ("keep", "bot_question_unanswered"))

    def test_running_signal_keeps_recent_collaboration(self) -> None:
        result = CLASSIFIER.classify(facts([
            message(701, "please upgrade", False),
            message(702, "still running", True),
        ]))
        self.assertEqual(result["verdict"], "keep")
        self.assertNotEqual(result["reasonCode"], "collab_answered_idle")

    def test_completed_bot_only_operational_archives(self) -> None:
        result = CLASSIFIER.classify(facts(
            [message(801, "completed successfully", True)],
            name="🤖 maintenance",
            humanInitiated=False,
            hadHistoricalHumanParticipation=False,
            lastMessageAgeMinutes=130,
        ))
        self.assertEqual((result["verdict"], result["reasonCode"]), ("archive", "op_done_no_human"))


if __name__ == "__main__":
    unittest.main()
