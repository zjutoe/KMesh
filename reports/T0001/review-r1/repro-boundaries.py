"""Codex review evidence only: synthetic failures, no real torch/CUDA import."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
from unittest.mock import patch

import pytest

import kmesh.cli as cli
from kmesh.utils import environment

review_dir = Path(__file__).resolve().parent
results = []

for name, runtime, available, count in [
    ("missing-version", "missing", True, 1),
    ("runtime-not-string", 42, True, 1),
    ("availability-none", "12.6", None, 1),
    ("count-fraction", "12.6", True, 1.5),
    ("count-bool", "12.6", True, True),
]:
    fake_torch = types.ModuleType("torch")
    if runtime != "missing":
        fake_torch.version = types.SimpleNamespace(cuda=runtime)
    fake_torch.cuda = types.SimpleNamespace(
        is_available=lambda: available,
        device_count=lambda: count,
        get_device_properties=lambda index: types.SimpleNamespace(
            name="Synthetic GPU", total_memory=1024
        ),
    )
    out = review_dir / f"synthetic-{name}.json"
    stdout, stderr = io.StringIO(), io.StringIO()
    row = {"case": name, "synthetic": True}
    with patch.dict(sys.modules, {"torch": fake_torch}), patch.object(
        environment, "version", return_value="fixture-version"
    ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            row["cli_return"] = cli.main(["doctor", "--out", str(out)])
        except Exception as exc:
            row["exception"] = f"{type(exc).__name__}: {exc}"
    row["report_exists"] = out.exists()
    if out.exists():
        report = json.loads(out.read_text())
        row.update(status=report["status"], cuda=report["cuda"], errors=report["errors"])
    row.update(stdout=stdout.getvalue(), stderr=stderr.getvalue())
    results.append(row)

# Exercise the submitted test unchanged against an in-memory regression.
# The regression calls the collector before help. No source files are changed.
spec = importlib.util.spec_from_file_location("review_test_doctor", "tests/test_doctor.py")
test_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_module)
calls = []
real_main = cli.main
captured = io.StringIO()


def spy_collector():
    calls.append("collector-called")
    return {}


def main_with_help_regression(argv):
    cli.collect_environment()
    return real_main(argv)


fake_capsys = types.SimpleNamespace(
    readouterr=lambda: types.SimpleNamespace(out=captured.getvalue(), err="")
)
with pytest.MonkeyPatch.context() as monkeypatch:
    monkeypatch.setattr(cli, "collect_environment", spy_collector)
    monkeypatch.setattr(cli, "main", main_with_help_regression)
    with contextlib.redirect_stdout(captured):
        test_module.test_help_does_not_call_collector(monkeypatch, fake_capsys)
results.append({
    "case": "help-test-with-in-memory-regression",
    "submitted_test_passed": True,
    "unexpected_collector_calls": len(calls),
})
print(json.dumps(results, indent=2))
