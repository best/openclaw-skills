#!/usr/bin/env python3
"""
Validate feed-score output against the active candidate batch.

This catches a high-risk failure mode where the scorer treats the collector's
seen.json as the duplicate source. The collector records current candidates in
seen.json before scoring, so comparing against seen.json can mark every current
candidate as a duplicate of itself.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}")


def as_items(value, field_name: str):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("results", "candidates", "items", "entries"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
    raise ValueError(f"{field_name} must be a list or an object with a list field")


def clean_string(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def normalize_title(value) -> str:
    return " ".join(clean_string(value).lower().split())


def normalize_url(value) -> str:
    url = clean_string(value)
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return url.rstrip("/")


def item_url(item) -> str:
    if not isinstance(item, dict):
        return ""
    return normalize_url(item.get("sourceUrl")) or normalize_url(item.get("url"))


def item_score(item) -> float | None:
    if not isinstance(item, dict):
        return None
    try:
        return float(item.get("score"))
    except (TypeError, ValueError):
        return None


def fail(errors: list[str]) -> int:
    print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scored_results", type=Path)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow scored results to cover only part of candidates.json.",
    )
    parser.add_argument(
        "--publish-threshold",
        type=float,
        default=7.0,
        help="Minimum score allowed for publish verdict.",
    )
    args = parser.parse_args()

    errors: list[str] = []
    try:
        scored = load_json(args.scored_results)
        candidates_raw = load_json(args.candidates)
        results = as_items(scored, "scored results")
        candidates = as_items(candidates_raw, "candidates")
    except ValueError as exc:
        return fail([str(exc)])

    if not isinstance(scored, dict):
        errors.append("scored-results.json must be a top-level object, not a bare array")

    candidate_by_url = {}
    for idx, candidate in enumerate(candidates, 1):
        url = item_url(candidate)
        if not url:
            errors.append(f"candidate #{idx} missing valid url/sourceUrl")
            continue
        candidate_by_url[url] = candidate

    result_urls = []
    publish_count = 0
    skip_count = 0
    duplicate_count = 0
    for idx, result in enumerate(results, 1):
        if not isinstance(result, dict):
            errors.append(f"result #{idx} is not an object")
            continue
        verdict = result.get("verdict")
        if verdict not in {"publish", "skip"}:
            errors.append(f"result #{idx} has invalid verdict: {verdict!r}")
        if verdict == "publish":
            publish_count += 1
            score = item_score(result)
            if score is None:
                errors.append(f"publish result #{idx} missing numeric score")
            elif score < args.publish_threshold:
                errors.append(
                    f"publish result #{idx} score {score:g} is below threshold {args.publish_threshold:g}"
                )
        if verdict == "skip":
            skip_count += 1

        url = item_url(result)
        if not url:
            errors.append(f"result #{idx} missing valid url/sourceUrl")
            continue
        result_urls.append(url)

        reason = clean_string(result.get("reason")).lower()
        if verdict == "skip" and reason == "low_score":
            score = item_score(result)
            if score is None:
                errors.append(f"low_score result #{idx} missing numeric score")
            elif score >= args.publish_threshold:
                errors.append(
                    f"low_score result #{idx} score {score:g} is not below threshold {args.publish_threshold:g}"
                )
        if verdict == "skip" and reason == "duplicate":
            duplicate_count += 1
            duplicate_of = clean_string(result.get("duplicateOf"))
            if not duplicate_of:
                errors.append(f"duplicate result #{idx} missing duplicateOf")
            if normalize_title(duplicate_of) == normalize_title(result.get("title")):
                errors.append(
                    f"duplicate result #{idx} points duplicateOf to its own title"
                )
            if normalize_url(duplicate_of) and normalize_url(duplicate_of) == url:
                errors.append(f"duplicate result #{idx} points duplicateOf to its own URL")

    duplicates = [url for url, count in Counter(result_urls).items() if count > 1]
    if duplicates:
        errors.append(f"scored results contain repeated URLs: {duplicates[:5]}")

    unknown = sorted(set(result_urls) - set(candidate_by_url))
    if unknown:
        errors.append(f"scored results contain non-candidate URLs: {unknown[:5]}")

    missing = sorted(set(candidate_by_url) - set(result_urls))
    if missing and not args.allow_partial:
        errors.append(f"scored results missing candidate URLs: {missing[:5]}")

    if isinstance(scored, dict) and "evaluated" in scored:
        try:
            evaluated = int(scored.get("evaluated"))
        except (TypeError, ValueError):
            errors.append("scored-results.json evaluated must be an integer")
        else:
            if evaluated != len(results):
                errors.append(
                    f"scored-results.json evaluated={evaluated} does not match results count {len(results)}"
                )

    if results and skip_count == len(results) and duplicate_count == len(results):
        errors.append(
            "all candidates were skipped as duplicate; this usually means current "
            "candidates were compared against collector state instead of published items"
        )

    if errors:
        return fail(errors)

    print(
        json.dumps(
            {
                "ok": True,
                "candidates": len(candidates),
                "results": len(results),
                "publish": publish_count,
                "skip": skip_count,
                "duplicateSkips": duplicate_count,
                "publishThreshold": args.publish_threshold,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
