#!/usr/bin/env python3
"""Regression tests for generate-posts.py."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name('generate-posts.py')


class GeneratePostsTest(unittest.TestCase):
    def run_script(self, payload, repo_dir):
        results_path = Path(repo_dir) / 'scored-results.json'
        results_path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(results_path), '--repo-dir', str(repo_dir)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_publish_without_url_fails_before_writing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)
            proc = self.run_script({
                'results': [{
                    'verdict': 'publish',
                    'title': 'Broken publish item',
                    'description': '摘要',
                    'pubDatetime': '2026-05-05T00:00:00+08:00',
                    'category': '工程实践',
                    'tags': ['AI'],
                    'scoreBreakdown': '信息增量:7 内容质量:7 实用价值:7 减分:0',
                    'sourceType': 'rss',
                    'sourceName': 'Example',
                    'slug': 'broken-item',
                    'body': '## 要点\n\n内容\n\n## 🤖 AI 点评\n\n点评',
                }]
            }, repo_dir)

            self.assertNotEqual(proc.returncode, 0)
            summary = json.loads(proc.stdout)
            self.assertEqual(summary['generated'], 0)
            self.assertIn('missing/invalid sourceUrl or url', summary['errorDetails'][0]['errors'])
            self.assertFalse((repo_dir / 'src' / 'data' / 'blog').exists())

    def test_source_name_falls_back_to_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)
            proc = self.run_script({
                'results': [{
                    'verdict': 'publish',
                    'url': 'https://example.com/article',
                    'title': 'Valid publish item',
                    'description': '这是一条用于回归测试的摘要，确保来源字段会正确写入。',
                    'pubDatetime': '2026-05-05T00:00:00+08:00',
                    'collectedAt': '2026-05-05T08:00:00+08:00',
                    'category': '工程实践',
                    'tags': ['AI Agent', '工程实践'],
                    'featured': False,
                    'score': 7.2,
                    'scoreReason': '有工程参考价值',
                    'scoreBreakdown': '信息增量:7 内容质量:7 实用价值:8 减分:0',
                    'sourceType': 'rss',
                    'source': 'Example RSS',
                    'slug': 'valid-item',
                    'body': '## 要点\n\n内容\n\n## 🤖 AI 点评\n\n点评',
                }]
            }, repo_dir)

            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            summary = json.loads(proc.stdout)
            self.assertEqual(summary['generated'], 1)
            post = repo_dir / summary['files'][0]['file']
            content = post.read_text(encoding='utf-8')
            self.assertIn('sourceUrl: "https://example.com/article"', content)
            self.assertIn('sourceName: "Example RSS"', content)


if __name__ == '__main__':
    unittest.main()
