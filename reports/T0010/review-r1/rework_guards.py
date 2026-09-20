"""Check repaired tests against the submitted product and four known mutants.

Run through record_check.py RUN -- python this_script.py reports/T0010/RUN.
All product copies and pytest scratch stay under RUN/pytest-tmp.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]


def main():
    out = Path(sys.argv[1]).resolve()
    assert out.parent == ROOT / "reports/T0010" and out.is_dir()
    source = (ROOT / "src/kmesh/logic/depth.py").read_text()
    marker = "    if not isinstance(clauses, tuple):\n"
    assert source.count(marker) == 1
    variants = (
        ("submitted", source, None),
        ("unchecked_integer_format", source.replace(marker, "    str(clauses)\n" + marker, 1),
         "test_large_integer_diagnostics"),
        ("invalid_input_calls_enumerator", source.replace(marker, marker + "        enumerate_derivations(())\n", 1),
         "test_invalid_inputs_do_not_call_enumerator"),
        ("records_sorted_by_clause_position", source.replace(
            "    for record in records:\n", "    for record in sorted(records, key=lambda item: item.clause_index):\n", 1),
         "test_depth_invariant_under_transformations"),
        ("lazy_solver_import", source.replace(marker, "    from .engine import indexed_closure\n" + marker, 1),
         "test_g_depth_import_pulls_no_forbidden_modules"),
    )
    results = []
    for name, content, expected_failure in variants:
        workspace = out / "pytest-tmp" / name
        shutil.copytree(ROOT / "src/kmesh", workspace / "src/kmesh",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (workspace / "tests").mkdir()
        shutil.copy2(ROOT / "tests/test_depth.py", workspace / "tests/test_depth.py")
        (workspace / "src/kmesh/logic/depth.py").write_text(content)
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_depth.py",
                            "--basetemp", str(workspace / "tmp")],
                           cwd=workspace, capture_output=True, text=True, timeout=30,
                           env=os.environ | {"PYTHONPATH": str(workspace / "src"),
                                             "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "CUDA_VISIBLE_DEVICES": ""})
        (out / (name + ".stdout")).write_text(p.stdout)
        (out / (name + ".stderr")).write_text(p.stderr)
        failed_lines = [line for line in p.stdout.splitlines() if line.startswith("FAILED ")]
        passed = (p.returncode == 0 if expected_failure is None else
                  p.returncode == 1 and any(expected_failure in line for line in failed_lines))
        results.append(dict(variant=name, exit_code=p.returncode,
                            required_failed_test=expected_failure, guard_valid=passed))
    (out / "guards.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    assert all(row["guard_valid"] for row in results), "repair the named guards; keep all failure evidence"
    print("PASS: submitted tests pass and four known contract violations are rejected")


if __name__ == "__main__":
    main()
