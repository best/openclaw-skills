#!/usr/bin/env python3
"""Regression tests for feed_score_ctl.py and validate-score-results.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("feed_score_ctl.py")
VALIDATOR = Path(__file__).with_name("validate-score-results.py")


def candidate(idx: int) -> dict:
    return {
        "title": f"Candidate {idx}",
        "url": f"https://example.com/{idx}",
        "source": "Example",
        "sourceType": "rss",
        "category": "Developer",
        "pubDatetime": "2026-06-15T00:00:00Z",
        "snippet": "Short candidate snippet.",
        "collectedAt": "2026-06-15T08:00:00+08:00",
    }


class ScoreRunnerTest(unittest.TestCase):
    def init_repo(self, root: Path, count: int = 35) -> Path:
        repo = root / "feed"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        (repo / "data").mkdir()
        (repo / "data" / "candidates.json").write_text(
            json.dumps([candidate(i) for i in range(count)], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "data/candidates.json"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True)
        remote = root / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
        return repo

    def run_ctl(self, repo: Path, task: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(repo), "--task", str(task), *args],
            text=True,
            capture_output=True,
            check=False,
            env=proc_env,
        )

    def test_batch_finalize_validates_task_batch_and_keeps_remaining(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.init_repo(root)
            task = root / "task.json"

            prep = self.run_ctl(repo, task, "prepare", "--limit", "30", "--dry-run")
            self.assertEqual(prep.returncode, 0, prep.stderr + prep.stdout)
            prepared = json.loads(prep.stdout)
            self.assertEqual(prepared["status"], "needs_scoring")
            self.assertEqual(prepared["candidates"], 30)
            self.assertEqual(prepared["remainingCandidates"], 5)

            task_data = json.loads(task.read_text(encoding="utf-8"))
            results = [
                {
                    "verdict": "skip",
                    "url": item["url"],
                    "title": item["title"],
                    "reason": "low_score",
                    "score": 6.0,
                }
                for item in task_data["candidates"]
            ]
            (repo / "data" / "scored-results.json").write_text(
                json.dumps({"evaluated": len(results), "results": results}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            final = self.run_ctl(repo, task, "finalize", "--dry-run")
            self.assertEqual(final.returncode, 0, final.stderr + final.stdout)
            finalized = json.loads(final.stdout)
            self.assertEqual(finalized["status"], "ok")
            self.assertEqual(finalized["validation"]["candidates"], 30)
            self.assertEqual(finalized["validation"]["results"], 30)

    def test_validator_rejects_non_batch_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.json"
            scored = root / "scored.json"
            candidates.write_text(json.dumps([candidate(1)], indent=2), encoding="utf-8")
            scored.write_text(
                json.dumps(
                    {
                        "evaluated": 1,
                        "results": [
                            {
                                "verdict": "skip",
                                "url": "https://example.com/not-in-batch",
                                "title": "Outside batch",
                                "reason": "low_score",
                                "score": 6.0,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [sys.executable, str(VALIDATOR), str(scored), "--candidates", str(candidates)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("non-candidate URLs", proc.stdout)

    def test_finalize_skips_full_build_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.init_repo(root, count=1)
            task = root / "task.json"

            prep = self.run_ctl(repo, task, "prepare", "--limit", "1", "--dry-run")
            self.assertEqual(prep.returncode, 0, prep.stderr + prep.stdout)
            task_data = json.loads(task.read_text(encoding="utf-8"))
            item = task_data["candidates"][0]
            (repo / "data" / "scored-results.json").write_text(
                json.dumps(
                    {
                        "evaluated": 1,
                        "scoredAt": "2026-06-15T17:00:00+08:00",
                        "results": [
                            {
                                "verdict": "publish",
                                "url": item["url"],
                                "title": item["title"],
                                "description": "A concise description for the generated AI Feed entry.",
                                "pubDatetime": item["pubDatetime"],
                                "collectedAt": item["collectedAt"],
                                "category": "工程实践",
                                "tags": ["LLM"],
                                "featured": False,
                                "score": 7.2,
                                "scoreReason": "Useful engineering signal with enough practical value.",
                                "scoreBreakdown": "信息增量:7 内容质量:7 实用价值:8 减分:0",
                                "sourceType": "rss",
                                "sourceName": "Example",
                                "slug": "candidate-one",
                                "body": "## 要点\n\nThis is the useful point.\n\n## 🤖 AI 点评\n\nThis is the analysis.",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            final = self.run_ctl(repo, task, "finalize", env={"FEED_SCORE_RUN_BUILD": "0"})
            self.assertEqual(final.returncode, 0, final.stderr + final.stdout)
            finalized = json.loads(final.stdout)
            self.assertEqual(finalized["status"], "ok")
            self.assertEqual(finalized["generated"], 1)
            self.assertFalse(finalized["buildRan"])
            self.assertTrue(finalized["buildSkipped"])
            self.assertIn("build=skipped", finalized["message"])

    def test_recent_batch_guard_stops_immediate_second_prepare(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.init_repo(root, count=2)
            task = root / "task.json"

            prep = self.run_ctl(repo, task, "prepare", "--limit", "1", "--dry-run")
            self.assertEqual(prep.returncode, 0, prep.stderr + prep.stdout)
            task_data = json.loads(task.read_text(encoding="utf-8"))
            item = task_data["candidates"][0]
            (repo / "data" / "scored-results.json").write_text(
                json.dumps(
                    {
                        "evaluated": 1,
                        "scoredAt": "2026-06-15T17:00:00+08:00",
                        "results": [
                            {
                                "verdict": "skip",
                                "url": item["url"],
                                "title": item["title"],
                                "reason": "low_score",
                                "score": 6.0,
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            final = self.run_ctl(repo, task, "finalize", env={"FEED_SCORE_RUN_BUILD": "0"})
            self.assertEqual(final.returncode, 0, final.stderr + final.stdout)
            second = self.run_ctl(repo, task, "prepare", "--limit", "1")
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            guarded = json.loads(second.stdout)
            self.assertEqual(guarded["status"], "no_content")
            self.assertTrue(guarded["guarded"])
            self.assertEqual(guarded["candidates"], 1)


if __name__ == "__main__":
    unittest.main()
