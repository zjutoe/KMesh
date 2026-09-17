#!/usr/bin/env python3
"""T0006 R2 hygiene audit for the T0006-proof-verifier branch.

Verifies, on top of `git diff --check`:
  1. The two new deliverables exist, are non-empty, and match the frozen R1
     content hashes (test_proof.py is the R2 rework hash; proof.py and
     __init__.py are unchanged from R1, per the R2 contract).
  2. `kmesh/logic/__init__.py` still has the frozen zero-import content
     hash.
  3. Every T0001-T0005 product/test blob is byte-identical to the branch
     baseline (compared against HEAD via git).
  4. The current working-tree mutation set is exactly the allowed set:
     this task's files plus the external worktree edits Codex made during
     the round (research plan v0.1.2, decisions D21-D24, T0005 doc
     corrections, paper framework). Anything else fails.
  5. The checked text files end with a newline, carry no trailing
     whitespace, and every relative Markdown link in README.md and
     docs/implementation_status.md resolves.

Exit status: 0 only when every check passes.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

FROZEN = {
    "src/kmesh/logic/proof.py":
        "008bdd3633a5d2327cd711b7c9de7149df86b588632db659a23bf34207963daa",
    "tests/test_proof.py":
        "21e099b8939e35f90e188062973d0b5e553e07e50f86127441d399a8848897c3",
    "src/kmesh/logic/__init__.py":
        "649c92a60e8c3477bce80d2ec0beda7ab14d20ed776fdc4e715a11fd5d15fa96",
}

T0001_T0005_BLOBS = [
    "src/kmesh/logic/types.py",
    "src/kmesh/logic/engine.py",
    "src/kmesh/logic/reference_engine.py",
    "tests/test_logic_types.py",
    "tests/test_engine.py",
    "tests/test_reference_engine.py",
    "docs/handoffs/T0001-bootstrap-doctor.md",
    "docs/handoffs/T0002-model-config.md",
    "docs/handoffs/T0003-logic-types.md",
    "docs/handoffs/T0004-reference-closure.md",
]

EXPECTED_STATUS = [
    # This task (Pi R1):
    " M README.md",
    "?? docs/handoffs/T0006-proof-verifier.md",
    " M docs/implementation_status.md",
    "?? reports/T0006/",
    "?? src/kmesh/logic/proof.py",
    "?? tests/test_proof.py",
    # External edits by Codex in the shared worktree during this round
    # (plan v0.1.2 / D21-D24 / paper framework / T0005 doc corrections):
    " M KMesh_Research_Plan_v0.1.md",
    " M docs/decisions.md",
    " M docs/handoffs/T0005-indexed-closure.md",
    "?? KMesh_Paper_Framework_v0.1.md",
]

CHECKED_TEXT = [
    "src/kmesh/logic/proof.py",
    "tests/test_proof.py",
    "README.md",
    "docs/implementation_status.md",
    "docs/handoffs/T0006-proof-verifier.md",
]


def main() -> int:
    failures: list[str] = []

    # 1 + 2. New deliverables and the zero-import package init hash.
    for name, digest in FROZEN.items():
        path = REPO_ROOT / name
        if not path.is_file():
            failures.append("missing file: " + name)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            failures.append("hash mismatch for " + name)

    # 3. Frozen T0001-T0005 blobs identical to HEAD (the two new files are
    #    untracked and covered by the FROZEN hash check instead).
    for name in T0001_T0005_BLOBS:
        path = REPO_ROOT / name
        if not path.is_file():
            failures.append("missing frozen file: " + name)
            continue
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD:" + name],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        if head.returncode != 0:
            failures.append("not in HEAD (unexpected): " + name)
            continue
        work = subprocess.run(
            ["git", "hash-object", "--", str(path)],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
        if work.stdout.strip() != head.stdout.strip():
            failures.append("working tree differs from HEAD: " + name)

    # 4. Exact mutation set.
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    if sorted(status) != sorted(EXPECTED_STATUS):
        failures.append("git status mismatch:\n actual:  %s\n expected: %s"
                        % ("\n    ".join(status),
                           "\n    ".join(EXPECTED_STATUS)))

    # 5. Hygiene: final newline, trailing whitespace, relative links.
    for name in CHECKED_TEXT:
        path = REPO_ROOT / name
        data = path.read_bytes()
        if not data.endswith(b"\n"):
            failures.append("missing final newline: " + name)
        for lineno, line in enumerate(
                data.decode("utf-8").splitlines(), start=1):
            if line != line.rstrip():
                failures.append("trailing whitespace %s:%d" % (name, lineno))
                break
    for name in ("README.md", "docs/implementation_status.md"):
        md = (REPO_ROOT / name).read_text(encoding="utf-8")
        for match in re.finditer(r"\]\(([^)\s#]+)\)", md):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (REPO_ROOT / name).parent.joinpath(target).exists():
                failures.append("broken link in %s: %s" % (name, target))

    if failures:
        for item in failures:
            print("DIFF-CHECK FAIL: " + item)
        return 1
    print("DIFF-CHECK OK: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
