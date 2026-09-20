"""Run one named T0010 check through the immutable recorder.

Usage: .venv/bin/python reports/T0010/run_checks.py RUN PHASE
PHASE is preflight, focused, full or docs. No directory is reused.
"""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TASK = "reports/T0010"
PYTHON = ".venv/bin/python"
TESTS = [
    "tests/test_depth.py", "tests/test_proof_enumeration.py", "tests/test_derivations.py",
    "tests/test_dependency.py", "tests/test_proof.py", "tests/test_engine.py",
    "tests/test_reference_engine.py", "tests/test_logic_types.py",
    "tests/test_config.py", "tests/test_doctor.py",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("phase", choices=("preflight", "focused", "full", "docs"))
    args = parser.parse_args()
    if args.phase in ("focused", "full"):
        files = TESTS[:1] if args.phase == "focused" else TESTS
        command = [PYTHON, "-m", "pytest", "-q", *files,
                   "--basetemp", f"{TASK}/{args.run}/pytest-tmp"]
    else:
        command = [PYTHON, f"{TASK}/check_delivery.py", args.phase]
    return subprocess.call(
        [PYTHON, f"{TASK}/record_check.py", args.run, "--", *command], cwd=ROOT
    )


if __name__ == "__main__":
    raise SystemExit(main())
