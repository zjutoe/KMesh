"""Codex-only review: recheck prior counterexamples and related YAML inputs."""
from pathlib import Path
import json
import os
import runpy
import subprocess
import sys
import time

import pytest
import yaml
import kmesh.config as config

root = Path.cwd()
review = root / "reports/T0002/review-r2"
run = review / "regressions"
run.mkdir(exist_ok=False)
results = {}
commands = []


def call(name, argv, overrides=None):
    start = time.monotonic()
    p = subprocess.run(argv, cwd=root, env=os.environ | (overrides or {}),
                       capture_output=True, timeout=60)
    (run / f"{name}.stdout").write_bytes(p.stdout)
    (run / f"{name}.stderr").write_bytes(p.stderr)
    row = dict(name=name, argv=argv, env_overrides=overrides or {},
               exit_code=p.returncode, elapsed_s=round(time.monotonic()-start, 3),
               stdout_empty=not p.stdout, traceback=b"Traceback" in p.stderr)
    commands.append(row)
    (run / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    return p, row


def inspect_error(function, value):
    try:
        function(value)
    except Exception as exc:
        return dict(exception=type(exc).__name__, message=str(exc),
                    controlled=isinstance(exc, config.ConfigError))
    return dict(exception=None, controlled=False)


old = root / "reports/T0002/review-r1/boundary-check"
for name in ("huge-dropout", "invalid-int-tag", "invalid-bool-tag", "invalid-date",
             "scalar-map-tag", "sequence-map-tag"):
    path = old / f"{name}.yaml"
    api = inspect_error(config.load_model_config, path)
    p, command = call(name, [sys.executable, "-m", "kmesh.cli", "config", "validate-model",
                              "--config", str(path)])
    passed = (api["controlled"] and str(path) in api["message"] and p.returncode == 1
              and not p.stdout and not command["traceback"] and str(path).encode() in p.stderr)
    results[name] = dict(api=api, cli=command, passed=passed)

source = (root / "configs/model_e0.yaml").read_text()
for name, replacement in (("empty-int-tag", "!!int ''"), ("empty-float-tag", "!!float ''"),
                          ("invalid-timestamp-tag", "!!timestamp nope")):
    path = run / f"{name}.yaml"
    path.write_text(source.replace("hidden_size: 256", f"hidden_size: {replacement}"))
    api = inspect_error(config.load_model_config, path)
    p, command = call(name, [sys.executable, "-m", "kmesh.cli", "config", "validate-model",
                              "--config", str(path)])
    results[name] = dict(api=api, cli=command,
                        passed=api["controlled"] and p.returncode == 1 and not p.stdout
                        and not command["traceback"] and str(path).encode() in p.stderr)

model = config.load_model_config(root / "configs/model_e0.yaml").as_dict()
for name, value in (("positive-huge-pure", 10**400), ("negative-huge-pure", -(10**400))):
    api = inspect_error(config.parse_model_config, model | {"dropout": value})
    results[name] = dict(api=api, passed=api["controlled"] and "model.dropout" in api["message"])

for command in ("help", "doctor"):
    name = f"missing-yaml-{command}"
    report_path = run / f"{name}.json"
    p, row = call(name, [sys.executable, "reports/T0002/review-r1/probe_yaml_missing.py",
                         "working-tree", command, str(report_path), "unused-baseline"],
                  {"CUDA_VISIBLE_DEVICES": ""})
    expected = 0 if command == "help" else 1
    passed = p.returncode == expected and not row["traceback"]
    if command == "doctor":
        report = json.loads(report_path.read_text()) if report_path.exists() else None
        passed = passed and report is not None and report["status"] == "error" and report["packages"]["PyYAML"] is None
        row["report"] = report
    results[name] = dict(cli=row, passed=passed)

# Exercise the actual revised tests with the corresponding rule bypassed in memory.
# The source and existing fixtures stay untouched; a caught pytest failure is expected.
namespace = runpy.run_path(str(root / "tests/test_config.py"))
fixtures = run / "mutation-fixtures"
fixtures.mkdir()
body, reason = namespace["_INVALID_CASES"][1]


def run_expected_test_failure(name, test_call, replacement):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(config, "_load_strict_yaml", replacement)
        try:
            test_call()
        except (AssertionError, pytest.fail.Exception) as exc:
            results[name] = dict(passed=True, exception=type(exc).__name__, message=str(exc))
        else:
            results[name] = dict(passed=False, message="test did not detect bypassed rule")


run_expected_test_failure("root-duplicate-test-detects-bypass",
    lambda: namespace["test_invalid_documents_are_rejected_for_the_labeled_reason"](fixtures, body, reason),
    yaml.safe_load)


def bypass_schema(text):
    document = yaml.safe_load(text)
    document["schema_version"] = 1
    return document


for version in ("2", "'1'", "true"):
    run_expected_test_failure(f"schema-test-detects-bypass-{version}",
        lambda: namespace["test_schema_version_rejects_wrong_value"](fixtures, version), bypass_schema)

(run / "results.json").write_text(json.dumps(results, indent=2) + "\n")
for name, row in results.items():
    print(name, "PASS" if row["passed"] else "FAIL", row.get("api", {}).get("exception", ""))
failed = [name for name, row in results.items() if not row["passed"]]
(run / "summary.json").write_text(json.dumps({"failed": failed, "result": "FAIL" if failed else "PASS"}, indent=2) + "\n")
raise SystemExit(1 if failed else 0)
