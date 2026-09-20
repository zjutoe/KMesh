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
    assert baseline["head"] == "153295c28788f27ef37e794c7c0ea19841accaa8"
    assert baseline["branch"] == "T0009-proof-enumeration"
    assert subprocess.check_output(
        ["git", "rev-parse", "origin/T0009-proof-enumeration"], cwd=ROOT, text=True
    ).strip() == baseline["head"]
    prior = json.loads((ROOT / "reports/T0009/review-r2/final-audit.json").read_text())
    assert prior["result"] == "PASS" and prior["task_status"] == "accepted"
    for name, digest in prior["accepted_files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    for name in ("src/kmesh/logic/depth.py", "tests/test_depth.py"):
        assert baseline["source_sha256"][name] is None, name
    assert Path(kmesh.__file__).resolve() == ROOT / "src/kmesh/__init__.py"
    baseline.update(
        python=sys.version, executable=sys.executable, kmesh_path=kmesh.__file__,
        packages={name: importlib.metadata.version(name) for name in ("kmesh", "pytest")},
        prior_accepted_regression="Codex T0009 review-r2-full: 679 passed; not rerun for planning",
        new_product_implemented=False,
    )
    assert sys.version_info[:3] == (3, 13, 9)
    assert baseline["packages"] == {"kmesh": "0.1.0", "pytest": "8.4.2"}
    path = ROOT / "reports/T0010/planning-baseline.json"
    with path.open("x") as stream:
        stream.write(json.dumps(baseline, indent=2) + "\n")
    print("PASS: accepted T0009 hashes, baseline, environment; new product/tests absent")


if __name__ == "__main__":
    main()
