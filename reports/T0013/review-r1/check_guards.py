"""Bounded isolated mutations for T0013; submitted source is never edited."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / sys.argv[1]
product = (ROOT / "src/kmesh/logic/proof_count.py").read_text()
test = (ROOT / "tests/test_proof_count.py").read_text()
loop = "    for proof in proofs:\n        keys.add(canonical_proof_key(clauses, query, proof, max_steps=max_proof_steps))\n"
swallow = "    for proof in proofs:\n        try:\n            keys.add(canonical_proof_key(clauses, query, proof, max_steps=max_proof_steps))\n        except Exception:\n            continue\n"


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


variants = [
    ("submitted", product, test, 0),
    ("raw_count", replace_once(product, "return len(keys)", "return len(proofs)"), test, 1),
    ("cap_two", replace_once(product, "return len(keys)", "return min(2, len(keys))"), test, 1),
    ("omit_key_budget", replace_once(product, ", proof, max_steps=max_proof_steps)", ", proof)"), test, 1),
    ("swallow_late_key_error", replace_once(product, loop, swallow), test, 1),
    ("root_only_import_guard", product, replace_once(test, 'name == root or name.startswith(root + ".")', 'name == root'), 0),
]
rows = []
for name, source, tests, expected_exit in variants:
    case = OUT / "pytest-tmp/cases" / name
    case.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT / "src", case / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    (case / "tests").mkdir()
    (case / "src/kmesh/logic/proof_count.py").write_text(source)
    (case / "tests/test_proof_count.py").write_text(tests)
    argv = [sys.executable, "-m", "pytest", "-q", "tests/test_proof_count.py", "--basetemp", str(case / "tmp")]
    env = os.environ | {"PYTHONPATH": str(case / "src"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "CUDA_VISIBLE_DEVICES": ""}
    run = subprocess.run(argv, cwd=case, env=env, capture_output=True, timeout=30)
    (OUT / f"{name}.stdout.txt").write_bytes(run.stdout)
    (OUT / f"{name}.stderr.txt").write_bytes(run.stderr)
    row = dict(name=name, argv=argv, cwd=str(case), exit_code=run.returncode,
               expected_exit=expected_exit, summary=run.stdout.decode().strip().splitlines()[-1])
    rows.append(row)
    print(name, run.returncode, row["summary"])
    assert run.returncode == expected_exit, row
with (OUT / "guards.json").open("x") as stream:
    stream.write(json.dumps(dict(result="COMPLETED", submitted_passed=True,
        rejected_product_mutants=4, surviving_guard_mutants=["root_only_import_guard"], runs=rows), indent=2) + "\n")

