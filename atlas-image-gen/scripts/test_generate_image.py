#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("generate_image.py")
SPEC = importlib.util.spec_from_file_location("atlas_generate_image", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class GenerateImageTests(unittest.TestCase):
    def test_submission_is_called_once_without_retry(self):
        calls = []

        def failing_open(request, timeout):
            calls.append((request.method, timeout))
            raise urllib.error.URLError("temporary failure")

        with self.assertRaisesRegex(module.AtlasError, "POST was not retried"):
            module.submit_generation(
                api_base="https://api.example.com",
                api_key="test-key",
                payload={"model": "model", "prompt": "prompt"},
                open_url=failing_open,
            )
        self.assertEqual(calls, [("POST", 60)])

    def test_polling_accepts_nested_response_and_retries_get(self):
        responses = [
            urllib.error.URLError("temporary"),
            {"data": {"status": "processing", "id": "pred-1"}},
            {"data": {"status": "succeeded", "id": "pred-1", "outputs": ["https://cdn.example.com/a.png"]}},
        ]
        calls = []

        def fake_open(request, timeout):
            calls.append(request.method)
            value = responses.pop(0)
            if isinstance(value, Exception):
                raise value
            return FakeResponse(value)

        clock = iter([0.0, 0.0, 0.0, 0.0, 0.0])
        result = module.wait_for_prediction(
            {"data": {"id": "pred-1", "status": "queued"}},
            api_base="https://api.example.com",
            api_key="test-key",
            poll_interval=0,
            timeout=10,
            open_url=fake_open,
            sleep=lambda _seconds: None,
            monotonic=lambda: next(clock),
        )
        self.assertEqual(module.output_urls(result), ["https://cdn.example.com/a.png"])
        self.assertEqual(calls, ["GET", "GET", "GET"])

    def test_result_url_from_submission_is_used(self):
        initial = {
            "id": "pred-2",
            "status": "queued",
            "urls": {"result": "https://api.example.com/result/pred-2"},
        }
        self.assertEqual(
            module.prediction_url("https://api.example.com", initial, "pred-2"),
            "https://api.example.com/result/pred-2",
        )

    def test_result_url_cannot_send_key_to_another_host(self):
        initial = {
            "id": "pred-2",
            "status": "queued",
            "urls": {"result": "https://attacker.example.net/result/pred-2"},
        }
        with self.assertRaisesRegex(module.AtlasError, "configured Atlas Cloud API host"):
            module.prediction_url("https://api.example.com", initial, "pred-2")

    def test_top_level_output_string_is_normalized(self):
        self.assertEqual(
            module.output_urls({"status": "succeeded", "output": "https://cdn.example.com/a.webp"}),
            ["https://cdn.example.com/a.webp"],
        )
        self.assertEqual(module.output_urls({"output": "http://unsafe.example.com/a.png"}), [])

    def test_download_detects_png_and_writes_output(self):
        png = b"\x89PNG\r\n\x1a\n" + b"test-data"
        with tempfile.TemporaryDirectory() as directory:
            paths = module.download_outputs(
                ["https://cdn.example.com/a"],
                filename=str(Path(directory) / "result.jpg"),
                open_url=lambda _request, timeout: FakeResponse(png),
                sleep=lambda _seconds: None,
            )
            self.assertEqual(paths[0].suffix, ".png")
            self.assertEqual(paths[0].read_bytes(), png)


if __name__ == "__main__":
    unittest.main()
