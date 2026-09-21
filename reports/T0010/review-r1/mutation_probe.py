"""Run submitted tests against isolated, intentionally wrong product copies.

Exit 0 means the probe ran as expected, not that mutants satisfy the contract.
The real product and test files are never edited.
"""
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path.cwd()
OUT = ROOT / "reports/T0010/review-r1-mutations"


def main():
    source = (ROOT / "src/kmesh/logic/depth.py").read_text()
    marker = "    if not isinstance(clauses, tuple):\n"
    assert source.count(marker) == 1
    variants = {
        "unchecked_integer_format": source.replace(marker, "    str(clauses)\n" + marker, 1),
        "lazy_solver_import": source.replace(marker, "    from .engine import indexed_closure\n" + marker, 1),
        "invalid_input_calls_enumerator": source.replace(marker, marker + "        enumerate_derivations(())\n", 1),
        "records_sorted_by_clause_position": source.replace(
            "    for record in records:\n",
            "    for record in sorted(records, key=lambda item: item.clause_index):\n", 1),
    }
    result = []
    for name, mutant in variants.items():
        assert mutant != source, name
        workspace = OUT / "pytest-tmp" / name
        shutil.copytree(ROOT / "src/kmesh", workspace / "src/kmesh",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (workspace / "tests").mkdir()
        shutil.copy2(ROOT / "tests/test_depth.py", workspace / "tests/test_depth.py")
        (workspace / "src/kmesh/logic/depth.py").write_text(mutant)
        (OUT / (name + ".diff")).write_text("".join(difflib.unified_diff(
            source.splitlines(True), mutant.splitlines(True), fromfile="submitted/depth.py", tofile=name + "/depth.py")))
        argv = [sys.executable, "-m", "pytest", "-q", "tests/test_depth.py",
                "--basetemp", str(workspace / "tmp")]
        p = subprocess.run(argv, cwd=workspace, capture_output=True, timeout=30,
                           env=os.environ | {"PYTHONPATH": str(workspace / "src"),
                                             "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "CUDA_VISIBLE_DEVICES": ""})
        (OUT / (name + ".stdout")).write_bytes(p.stdout)
        (OUT / (name + ".stderr")).write_bytes(p.stderr)
        result.append(dict(name=name, argv=argv, cwd=str(workspace), exit_code=p.returncode,
                           mutant_sha256=hashlib.sha256(mutant.encode()).hexdigest(),
                           stdout=p.stdout.decode(), stderr=p.stderr.decode()))
    (OUT / "findings.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps([{k: x[k] for k in ("name", "exit_code", "stdout")} for x in result], indent=2))
    assert all(x["exit_code"] == 0 and "40 passed" in x["stdout"] for x in result)
    print("CONFIRMED: four contract-breaking mutants survive all 40 submitted tests")


if __name__ == "__main__":
    main()
