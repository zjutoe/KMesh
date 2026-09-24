"""Record the accepted dependency baseline before T0013 planning edits."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

import kmesh

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "reports/T0013"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def main():
    head = git("rev-parse", "HEAD")
    assert head.startswith("e576c77")
    assert git("branch", "--show-current") == "T0012-proof-key"
    assert not git("diff", "HEAD", "--name-only"), "tracked baseline must be clean"
    for name in ("src/kmesh/logic/proof_count.py", "tests/test_proof_count.py"):
        assert not (ROOT / name).exists(), name
    audit = json.loads((ROOT / "reports/T0012/review-r5/final-audit.json").read_text())
    assert audit["task_status"] == "accepted"
    for name, digest in {**audit["accepted_files"], **audit["closure_document_sha256"], **audit["review_material_sha256"]}.items():
        assert sha(name) == digest, name
    tracked = [p for p in git("ls-files", "-z").split("\0") if p]
    result = dict(head=head, branch=git("branch", "--show-current"),
                  python=sys.version, executable=str(Path(sys.executable).absolute()),
                  kmesh_path=str(Path(kmesh.__file__).resolve()),
                  packages={n: importlib.metadata.version(n) for n in ("kmesh", "pytest", "PyYAML")},
                  tracked_sha256={n: sha(n) for n in tracked},
                  task="T0013", new_product_and_test_absent=True)
    out = TASK / "planning-baseline.json"
    with out.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print("PASS: accepted T0012 matches commit; clean tracked baseline; new files absent")
    print(head, "tracked files:", len(tracked), "packages:", result["packages"])


if __name__ == "__main__":
    main()
