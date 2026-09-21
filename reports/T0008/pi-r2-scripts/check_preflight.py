#!/usr/bin/env python
"""T0008 R2 preflight: HEAD/branch check, frozen hashes, tree manifest.

Prints branch, HEAD, product/test hashes (pre-rework values) and writes
a sha256 manifest of every repo file (excluding .git/.venv/cache dirs)
to pi-r2-scripts/baseline_manifest.json used later by the R2 doc-check
as the frozen-materials baseline.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/mye/src/llm/KMesh")
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
PRODUCT = ROOT / "src/kmesh/logic/derivations.py"
TESTS = ROOT / "tests/test_derivations.py"
EXPECTED_PRODUCT = "32634248f401865d068b13758e133037a7a9bc3dcfa409526bc7df86a9aaf29b"
EXPECTED_TESTS_PRE_REWORK = "694c255ad5251ac1813b07ec335787b96a14e33b020a6aaaf865ac081c338fc0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    branch = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=True).stdout.strip()
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True).stdout.strip()
    print("branch:", branch)
    print("head:", head)
    assert head == "a9441250626f087dc8dbc1f560b7fbe3fe92488b", head
    product = sha256(PRODUCT)
    tests = sha256(TESTS)
    print("product:", product)
    print("tests_pre_rework:", tests)
    assert product == EXPECTED_PRODUCT, "product modified before R2"
    assert tests == EXPECTED_TESTS_PRE_REWORK, "tests modified before R2"
    manifest = {}
    count = 0
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if rel.suffix == ".pyc":
            continue
        manifest[str(rel)] = sha256(path)
        count += 1
    out = Path(__file__).with_name("baseline_manifest.json")
    out.write_text(json.dumps(manifest, indent=0, sort_keys=True) + "\n",
                   encoding="utf-8")
    print("manifest:", count, "files ->", out.relative_to(ROOT))
    print("PREFLIGHT_OK")


if __name__ == "__main__":
    main()
