import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path.cwd()
run = Path(sys.argv[1]).resolve()
run.mkdir(parents=True, exist_ok=False)
source = (root / "configs/model_e0.yaml").read_text(encoding="utf-8")
assert source.count("heads: 4") == 1
invalid = run / "invalid-model.yaml"
invalid.write_text(source.replace("heads: 4", "heads: 3"), encoding="utf-8")
checks = [
    ("module-help", [".venv/bin/python", "-m", "kmesh.cli", "--help"], {}, 0),
    ("config-help", [".venv/bin/python", "-m", "kmesh.cli", "config", "--help"], {}, 0),
    ("model-help", [".venv/bin/python", "-m", "kmesh.cli", "config", "validate-model", "--help"], {}, 0),
    ("module-valid", [".venv/bin/python", "-m", "kmesh.cli", "config", "validate-model", "--config", "configs/model_e0.yaml"], {}, 0),
    ("console-valid", [".venv/bin/kmesh", "config", "validate-model", "--config", "configs/model_e0.yaml"], {}, 0),
    ("invalid-model", [".venv/bin/python", "-m", "kmesh.cli", "config", "validate-model", "--config", str(invalid)], {}, 1),
    ("missing-argument", [".venv/bin/kmesh", "config", "validate-model"], {}, 2),
    ("tests", [".venv/bin/python", "-m", "pytest", "-q", "tests/test_config.py", "tests/test_doctor.py", "--basetemp", str(run / "pytest-tmp")], {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}, 0),
    ("doctor-regression", [".venv/bin/python", "-m", "kmesh.cli", "doctor", "--out", str(run / "doctor-cpu.json")], {"CUDA_VISIBLE_DEVICES": ""}, 0),
    ("diff-check", ["git", "diff", "--check"], {}, 0),
]
records = []
for name, argv, overrides, expected in checks:
    start = time.monotonic()
    limit = 120 if name == "tests" else 60
    try:
        p = subprocess.run(argv, cwd=root, env=os.environ | overrides,
                           capture_output=True, timeout=limit)
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        code, out, err = 124, exc.stdout or b"", exc.stderr or b""
    (run / f"{name}.stdout").write_bytes(out)
    (run / f"{name}.stderr").write_bytes(err)
    records.append(dict(name=name, argv=argv, cwd=str(root), env_overrides=overrides,
                        expected_exit=expected, exit_code=code, timeout_s=limit,
                        elapsed_s=round(time.monotonic() - start, 3)))
    (run / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
    print(name, code, flush=True)
    if code != expected:
        raise SystemExit(1)
left = json.loads((run / "module-valid.stdout").read_text(encoding="utf-8"))
right = json.loads((run / "console-valid.stdout").read_text(encoding="utf-8"))
assert left == right
assert set(left) == {"schema_version", "validation_scope", "model"}
assert left["schema_version"] == 1 and left["validation_scope"] == "model_only"
assert left["model"]["hidden_size"] == 256 and left["model"]["heads"] == 4
assert (run / "module-valid.stderr").read_bytes() == b""
assert (run / "console-valid.stderr").read_bytes() == b""
assert (run / "invalid-model.stdout").read_bytes() == b""
assert b"model.hidden_size" in (run / "invalid-model.stderr").read_bytes()
doctor = json.loads((run / "doctor-cpu.json").read_text(encoding="utf-8"))
assert doctor["status"] == "cpu_only" and doctor["errors"] == []
(run / "verification.json").write_text(json.dumps({"result": "PASS", "entrypoints_equal": True, "scope": "model_only", "doctor_regression": "cpu_only"}, indent=2) + "\n")
print("PASS: T0002 verification completed")
