"""R3: full focused control, then only the three affected tests on bad copies.

The fourth bad copy alters the swap fixture helper, not the product. It proves
the repaired test actually requires H8's two distinct premises to exchange.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
NAMES = ("test_c4_validation_priority", "test_d2b_exception_instance_identity",
         "test_depth_invariant_under_transformations")


def main():
    out = Path(sys.argv[1]).resolve()
    assert out.parent == ROOT / "reports/T0010" and out.is_dir()
    source = (ROOT / "src/kmesh/logic/depth.py").read_text()
    tests = (ROOT / "tests/test_depth.py").read_text()
    budgets = '        (max_fact_checks, "max_fact_checks"),\n        (max_derivations, "max_derivations"),\n'
    ground = '    if not query.is_ground:\n        raise LogicValidationError("depth.query must be a ground Atom")\n'
    call = ('    records = enumerate_derivations(\n'
            '        clauses, max_fact_checks=max_fact_checks,\n'
            '        max_derivations=max_derivations)\n')
    helper = 'def _swap_twin_premises(world):\n'
    assert all(source.count(s) == 1 for s in (budgets, ground, call))
    assert tests.count(helper) == 1
    wrapped = ('    try:\n' + ''.join('    ' + line for line in call.splitlines(True)) +
               '    except LogicValidationError as exc:\n'
               '        raise LogicValidationError(str(exc)) from exc\n')
    variants = (
        ("submitted", source, tests, None),
        ("reconstruct_logic_error", source.replace(call, wrapped), tests, NAMES[1]),
        ("budget_d_before_c", source.replace(budgets,
            '        (max_derivations, "max_derivations"),\n        (max_fact_checks, "max_fact_checks"),\n'), tests, NAMES[0]),
        ("ground_check_after_budgets", source.replace(ground, '').replace(call, ground + call), tests, NAMES[0]),
        ("swap_helper_noop", source, tests.replace(helper, helper + '    return world\n', 1), NAMES[2]),
    )
    results = []
    for name, product_text, test_text, required_test in variants:
        work = out / "pytest-tmp" / name
        shutil.copytree(ROOT / "src/kmesh", work / "src/kmesh", ignore=shutil.ignore_patterns("__pycache__"))
        (work / "tests").mkdir()
        (work / "tests/test_depth.py").write_text(test_text)
        (work / "src/kmesh/logic/depth.py").write_text(product_text)
        selection = ["tests/test_depth.py"] if required_test is None else [f"tests/test_depth.py::{n}" for n in NAMES]
        argv = [sys.executable, "-m", "pytest", "-q", *selection, "--basetemp", str(work / "tmp")]
        p = subprocess.run(argv, cwd=work, capture_output=True, text=True, timeout=30,
                           env=os.environ | {"PYTHONPATH": str(work / "src"),
                                             "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "CUDA_VISIBLE_DEVICES": ""})
        (out / (name + ".stdout")).write_text(p.stdout)
        (out / (name + ".stderr")).write_text(p.stderr)
        failures = [line for line in p.stdout.splitlines() if line.startswith("FAILED ")]
        ok = p.returncode == 0 if required_test is None else p.returncode == 1 and any(required_test in s for s in failures)
        results.append(dict(variant=name, argv=argv, exit_code=p.returncode,
                            required_failed_test=required_test, guard_valid=ok))
    (out / "guards.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    assert all(x["guard_valid"] for x in results)
    print("PASS: current focused suite and all four bounded R3 guards")


if __name__ == "__main__":
    main()
