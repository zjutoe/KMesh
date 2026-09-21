"""Codex handoff helper: capture one check in a new, immutable run directory.

Usage from the repository: .venv/bin/python reports/T0008/record_check.py RUN -- COMMAND ...
This is a verification helper, not part of the kmesh package.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    "src/kmesh/logic/derivations.py", "tests/test_derivations.py",
    "src/kmesh/logic/dependency.py", "tests/test_dependency.py",
    "src/kmesh/logic/proof.py", "tests/test_proof.py",
    "src/kmesh/logic/engine.py", "tests/test_engine.py",
    "src/kmesh/logic/reference_engine.py", "tests/test_reference_engine.py",
    "src/kmesh/logic/__init__.py", "src/kmesh/logic/types.py", "tests/test_logic_types.py",
    "src/kmesh/cli.py", "src/kmesh/config.py", "tests/test_config.py", "tests/test_doctor.py",
    "pyproject.toml", "reports/T0008/record_check.py",
)


def snapshot():
    result = {}
    for name, command in (
        ("head", ["git", "rev-parse", "HEAD"]),
        ("branch", ["git", "branch", "--show-current"]),
        ("status", ["git", "status", "--short"]),
    ):
        p = subprocess.run(command, cwd=ROOT, capture_output=True, check=True, timeout=10)
        result[name] = p.stdout.decode("utf-8")
    result["source_sha256"] = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() if (ROOT / path).is_file() else None
        for path in SOURCES
    }
    return result


def main():
    if len(sys.argv) < 4 or sys.argv[2] != "--" or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", sys.argv[1]):
        print("usage: record_check.py RUN -- COMMAND ...", file=sys.stderr)
        return 2
    run = ROOT / "reports/T0008" / sys.argv[1]
    if run.exists():
        print(f"record_check: refusing to reuse {run}", file=sys.stderr)
        return 2
    run.mkdir(exist_ok=False)
    argv = sys.argv[3:]
    overrides = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "CUDA_VISIBLE_DEVICES": ""}
    record = dict(started_at_utc=datetime.now(timezone.utc).isoformat(), argv=argv,
                  cwd=str(ROOT), env_overrides=overrides, timeout_s=120,
                  before=snapshot(), status="running")
    (run / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    start = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=ROOT, env=os.environ | overrides, capture_output=True, timeout=120)
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        code, out, err = 124, exc.stdout or b"", exc.stderr or b""
        record["timeout"] = True
    except OSError as exc:
        code, out, err = 127, b"", f"record_check: could not start command: {exc}\n".encode()
        record["launch_error"] = str(exc)
    (run / "stdout.txt").write_bytes(out)
    (run / "stderr.txt").write_bytes(err)
    record.update(status="finished", exit_code=code, elapsed_s=round(time.monotonic()-start, 3),
                  finished_at_utc=datetime.now(timezone.utc).isoformat(), after=snapshot(),
                  stdout_sha256=hashlib.sha256(out).hexdigest(), stderr_sha256=hashlib.sha256(err).hexdigest())
    (run / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"record_check: exit={code}; evidence={run.relative_to(ROOT)}")
    return code if code >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
