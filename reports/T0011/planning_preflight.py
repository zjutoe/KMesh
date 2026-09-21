"""Capture the accepted planning baseline; not a product implementation."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

import kmesh
from record_check import ROOT, snapshot


def main():
    baseline = snapshot()
    baseline["head"] = baseline["head"].strip()
    baseline["branch"] = baseline["branch"].strip()
    assert baseline["head"] == "4c457e21899f81274999855d905e66b2ba574798"
    assert baseline["branch"] == "T0010-minimum-depth"
    assert subprocess.check_output(
        ["git", "rev-parse", "origin/T0010-minimum-depth"], cwd=ROOT, text=True
    ).strip() == baseline["head"]
    prior = json.loads((ROOT / "reports/T0010/review-r3/final-audit.json").read_text())
    assert prior["result"] == "PASS" and prior["task_status"] == "accepted"
    for name, digest in prior["accepted_files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    for name in ("src/kmesh/logic/clause_key.py", "tests/test_clause_key.py"):
        assert baseline["source_sha256"][name] is None, name
    assert Path(kmesh.__file__).resolve() == ROOT / "src/kmesh/__init__.py"
    baseline.update(
        python=sys.version, executable=sys.executable, kmesh_path=kmesh.__file__,
        packages={name: importlib.metadata.version(name) for name in ("kmesh", "pytest")},
        prior_accepted_regression="T0010 accepted: Codex R3 focused 53; verified Pi R2 full 732; not rerun for planning",
        new_product_implemented=False,
    )
    assert sys.version_info[:3] == (3, 13, 9)
    assert baseline["packages"] == {"kmesh": "0.1.0", "pytest": "8.4.2"}
    path = ROOT / "reports/T0011/planning-baseline.json"
    with path.open("x") as stream:
        stream.write(json.dumps(baseline, indent=2) + "\n")
    print("PASS: accepted T0010 hashes, baseline, environment; new product/tests absent")


if __name__ == "__main__":
    main()
