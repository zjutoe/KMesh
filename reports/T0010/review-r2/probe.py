"""Demonstrate the bounded R2 test gaps on isolated product copies."""
import difflib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path.cwd()
OUT = ROOT / "reports/T0010/review-r2-probes"


def main():
    source = (ROOT / "src/kmesh/logic/depth.py").read_text()
    budgets = '        (max_fact_checks, "max_fact_checks"),\n        (max_derivations, "max_derivations"),\n'
    ground = '    if not query.is_ground:\n        raise LogicValidationError("depth.query must be a ground Atom")\n'
    call = ('    records = enumerate_derivations(\n'
            '        clauses, max_fact_checks=max_fact_checks,\n'
            '        max_derivations=max_derivations)\n')
    assert all(source.count(s) == 1 for s in (budgets, ground, call))
    wrapped = ('    try:\n' + ''.join('    ' + line for line in call.splitlines(True)) +
               '    except LogicValidationError as exc:\n'
               '        raise LogicValidationError(str(exc)) from exc\n')
    variants = {
        "reconstruct_logic_error": source.replace(call, wrapped),
        "budget_d_before_c": source.replace(budgets,
            '        (max_derivations, "max_derivations"),\n        (max_fact_checks, "max_fact_checks"),\n'),
        "ground_check_after_budgets": source.replace(ground, '').replace(call, ground + call),
    }
    rows = []
    for name, text in variants.items():
        work = OUT / "pytest-tmp" / name
        shutil.copytree(ROOT / "src/kmesh", work / "src/kmesh",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (work / "tests").mkdir()
        shutil.copy2(ROOT / "tests/test_depth.py", work / "tests/test_depth.py")
        (work / "src/kmesh/logic/depth.py").write_text(text)
        (OUT / (name + ".diff")).write_text("".join(difflib.unified_diff(
            source.splitlines(True), text.splitlines(True), fromfile="submitted/depth.py", tofile=name + "/depth.py")))
        argv = [sys.executable, "-m", "pytest", "-q", "tests/test_depth.py", "--basetemp", str(work / "tmp")]
        p = subprocess.run(argv, cwd=work, capture_output=True, text=True, timeout=30,
                           env=os.environ | {"PYTHONPATH": str(work / "src"),
                                             "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "CUDA_VISIBLE_DEVICES": ""})
        (OUT / (name + ".stdout")).write_text(p.stdout)
        (OUT / (name + ".stderr")).write_text(p.stderr)
        rows.append(dict(name=name, argv=argv, exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr))
    spec = importlib.util.spec_from_file_location("r2_tests", ROOT / "tests/test_depth.py")
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    before = tests.h8_world()
    after = tests._swap_twin_premises(before)
    assert before == after, "current H8 fixture unexpectedly changes"
    rule = before[-1]
    expected = tests.Clause(rule.body[::-1], rule.head)
    assert expected != rule
    swapped = before[:-1] + (expected,)
    assert tests.minimum_proof_depth(swapped, tests.atom("r", "a", "c")) == 1
    result = dict(mutants=rows, h8_swap_is_noop=before == after,
                  h8_original_body_args=[a.args for a in rule.body],
                  h8_required_body_args=[a.args for a in expected.body],
                  actual_product_on_correctly_swapped_h8=1)
    (OUT / "findings.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    assert all(r["exit_code"] == 0 and "53 passed" in r["stdout"] for r in rows)
    print("CONFIRMED: three contract-breaking mutants pass 53 tests; H8 swap is not executed")


if __name__ == "__main__":
    main()
