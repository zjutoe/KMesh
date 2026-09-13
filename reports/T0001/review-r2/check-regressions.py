"""Codex R1/R2 recheck; synthetic dependencies, no source edits or real CUDA."""

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
    assert not out.exists(), "Use a fresh evidence directory; do not overwrite."
    stdout, stderr = io.StringIO(), io.StringIO()
    with patch.dict(sys.modules, {"torch": fake_torch}), patch.object(
        environment, "version", return_value="fixture-version"
    ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = cli.main(["doctor", "--out", str(out)])
    report = json.loads(out.read_text())
    assert rc == 1 and report["status"] == "error" and report["errors"]
    assert report["torch_import_ok"] is True
    assert "error" in stderr.getvalue() and not stdout.getvalue()
    cuda = report["cuda"]
    if name in {"missing-version", "runtime-not-string"}:
        assert cuda["runtime_version"] is None
        assert cuda["available"] is True and cuda["device_count"] == 1
        assert len(cuda["devices"]) == 1
    else:
        assert cuda["runtime_version"] == "12.6"
        assert cuda["available"] is None and cuda["device_count"] is None
        assert cuda["devices"] == []
    results.append({
        "case": name, "result": "PASS", "synthetic": True,
        "cli_return": rc, "report": out.name, "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(), "cuda": cuda,
    })

# Run the submitted guard test unchanged, injecting an in-memory regression
# separately into the root help and doctor help paths.
spec = importlib.util.spec_from_file_location("review_test_doctor", "tests/test_doctor.py")
test_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_module)
real_main = cli.main
for target in (["--help"], ["doctor", "--help"]):
    captured = io.StringIO()
    attempts = []

    def main_with_regression(argv):
        if argv == target:
            attempts.append(list(argv))
            cli.collect_environment()
        return real_main(argv)

    fake_capsys = types.SimpleNamespace(
        readouterr=lambda: types.SimpleNamespace(out=captured.getvalue(), err="")
    )
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(cli, "main", main_with_regression)
        with contextlib.redirect_stdout(captured):
            with pytest.raises(AssertionError, match="collector must not run for --help") as exc:
                test_module.test_help_does_not_call_collector(monkeypatch, fake_capsys)
    assert attempts == [target]
    results.append({
        "case": "help-guard-detects-regression", "target": target,
        "result": "PASS", "caught": str(exc.value),
    })

print(json.dumps(results, indent=2))
