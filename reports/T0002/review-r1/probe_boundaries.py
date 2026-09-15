"""Codex review probes; writes only to a new review evidence directory."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time

from kmesh.config import ConfigError, load_model_config, parse_model_config

root = Path.cwd()
review = root / "reports/T0002/review-r1"
run = review / "boundary-check"
run.mkdir(exist_ok=False)
frozen = json.loads((review / "frozen-inputs.json").read_text())
for relative in ("src/kmesh/config.py", "src/kmesh/cli.py", "tests/test_config.py"):
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == frozen["file_sha256"][relative]

records = []


def call(name, argv, overrides=None):
    start = time.monotonic()
    p = subprocess.run(argv, cwd=root, env=os.environ | (overrides or {}),
                       capture_output=True, timeout=60)
    (run / f"{name}.stdout").write_bytes(p.stdout)
    (run / f"{name}.stderr").write_bytes(p.stderr)
    record = dict(name=name, argv=argv, env_overrides=overrides or {},
                  exit_code=p.returncode, elapsed_s=round(time.monotonic()-start, 3),
                  stdout_empty=not p.stdout, traceback=b"Traceback" in p.stderr)
    records.append(record)
    (run / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
    return record


def inspect_error(function, value):
    try:
        result = function(value)
    except Exception as exc:
        return dict(exception=type(exc).__name__, message=str(exc),
                    controlled=isinstance(exc, ConfigError))
    return dict(exception=None, controlled=False, result=result.as_dict())


source = (root / "configs/model_e0.yaml").read_text()
huge = 10**400
cases = {
    "huge-dropout": source.replace("dropout: 0.1", f"dropout: {huge}"),
    "invalid-int-tag": source.replace("hidden_size: 256", "hidden_size: !!int nope"),
    "invalid-bool-tag": source.replace("hidden_size: 256", "hidden_size: !!bool nope"),
    "invalid-date": source.replace("hidden_size: 256", "hidden_size: 2026-99-99"),
    "scalar-map-tag": "schema_version: 1\nmodel: !!map nope\n",
    "sequence-map-tag": "schema_version: 1\nmodel: !!map [a, b]\n",
    "control-root-duplicate": "schema_version: 1\n" + source,
    "control-schema-version": source.replace("schema_version: 1", "schema_version: 2"),
}
results = {}
for name, body in cases.items():
    path = run / f"{name}.yaml"
    path.write_text(body)
    api = inspect_error(load_model_config, path)
    command = call(name, [sys.executable, "-m", "kmesh.cli", "config", "validate-model",
                          "--config", str(path)])
    results[name] = dict(api=api, cli=command)

model = load_model_config(root / "configs/model_e0.yaml").as_dict()
results["huge-dropout-pure-api"] = inspect_error(parse_model_config, model | {"dropout": huge})

# Read the actual parametrized fixture objects; do not edit or reconstruct them.
namespace = runpy.run_path(str(root / "tests/test_config.py"))
test = namespace["test_invalid_yaml_documents_are_rejected"]
bodies = next(mark.args[1] for mark in test.pytestmark if mark.name == "parametrize")
for index in (1, 9, 10, 11):
    path = run / f"existing-fixture-{index}.yaml"
    path.write_text(bodies[index])
    results[f"existing-fixture-{index}"] = inspect_error(load_model_config, path)

# Preserve the actual baseline CLI for a before/after import-boundary comparison.
baseline = subprocess.run(["git", "show", f"{frozen['base_commit']}:src/kmesh/cli.py"],
                          cwd=root, capture_output=True, check=True).stdout
(run / "baseline-cli.py").write_bytes(baseline)
for version in ("baseline", "working-tree"):
    for command in ("help", "doctor"):
        name = f"yaml-missing-{version}-{command}"
        path = run / f"{name}.json"
        result = call(name, [sys.executable, str(review / "probe_yaml_missing.py"),
                            version, command, str(path), str(run / "baseline-cli.py")],
                      {"CUDA_VISIBLE_DEVICES": ""})
        result["report_exists"] = path.exists()
        if path.exists():
            report = json.loads(path.read_text())
            result["report_status"] = report["status"]
            result["pyyaml_metadata"] = report["packages"]["PyYAML"]
            result["report_errors"] = report["errors"]
        results[name] = result

(run / "results.json").write_text(json.dumps(results, indent=2) + "\n")
for name, result in results.items():
    if "api" in result:
        print(name, "API=" + str(result["api"]["exception"]),
              "CLI_TRACEBACK=" + str(result["cli"]["traceback"]))
    elif "exception" in result:
        print(name, result["exception"], result["message"])
    else:
        print(name, "EXIT=" + str(result["exit_code"]),
              "REPORT=" + str(result["report_exists"]), "TRACEBACK=" + str(result["traceback"]))
print("Probe collection completed; exit 0 means evidence saved, not acceptance.")
