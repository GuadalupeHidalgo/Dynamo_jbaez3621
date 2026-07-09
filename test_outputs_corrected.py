"""Verifier for dynamo/log-report.

One test per instruction.md success criterion. Ground truth is recomputed
independently from /app/access.log — nothing is hardcoded, so the tests stay
correct if the shipped log changes.
"""

import json
import re
from collections import Counter
from pathlib import Path

REPORT = Path("/app/report.json")
LOG = Path("/app/access.log")
REQUEST_RE = re.compile(r'"(?:GET|POST|PUT|DELETE|HEAD|PATCH) (\S+) ')


def _expected():
    """Helper (not a test): recompute ground truth from the input log."""
    paths, ips, total = Counter(), set(), 0
    with LOG.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            ips.add(line.split()[0])
            m = REQUEST_RE.search(line)
            if m:
                paths[m.group(1)] += 1
    return total, ips, paths


def _report():
    """Helper (not a test): load the agent's report."""
    assert REPORT.exists(), "no /app/report.json found"
    return json.loads(REPORT.read_text())


def test_report_is_single_json_object_with_exact_keys():
    """instruction.md: 'Write a single JSON object to /app/report.json with
    exactly these three keys' — file exists, parses as one JSON object, and
    its key set is exactly {total_requests, unique_ips, top_path}."""
    report = _report()
    assert isinstance(report, dict), "report.json is not a JSON object"
    assert set(report) == {"total_requests", "unique_ips", "top_path"}, \
        f"keys are {sorted(report)}"


def test_total_requests():
    """instruction.md: 'total_requests (integer) — the number of non-empty
    lines in the log.'"""
    total, _, _ = _expected()
    value = _report()["total_requests"]
    assert type(value) is int, "total_requests is not a JSON integer"
    assert value == total, f"expected {total}, got {value}"


def test_unique_ips():
    """instruction.md: 'unique_ips (integer) — the number of distinct client
    IP addresses; the client IP is the first whitespace-separated field.'"""
    _, ips, _ = _expected()
    value = _report()["unique_ips"]
    assert type(value) is int, "unique_ips is not a JSON integer"
    assert value == len(ips), f"expected {len(ips)}, got {value}"


def test_top_path():
    """instruction.md: 'top_path (string) — the request path that appears
    most often ... If several paths tie, any one of them is acceptable.'"""
    _, _, paths = _expected()
    assert paths, "verifier could not parse any request paths from the log"
    value = _report()["top_path"]
    assert type(value) is str, "top_path is not a JSON string"
    assert paths.get(value) == max(paths.values()), \
        f"{value!r} is not a most-frequent path"