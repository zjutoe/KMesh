"""Check the review record and freeze the needs_changes outcome, not acceptance."""
import ast
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "reports/T0013"
REVIEW = TASK / "review-r1"
DOCS = ("README.md", "docs/implementation_status.md", "docs/handoffs/T0013-proof-count.md", "reports/T0013/review-r1/review.md")


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


before = json.loads((REVIEW / "frozen-inputs.json").read_text())
for name, digest in before.items():
    if name not in DOCS[:3]:
        assert sha(name) == digest, name
links = 0
for name in DOCS:
    path = ROOT / name
    text = path.read_text()
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert all(line == line.rstrip() for line in text.splitlines()), name
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        uri = urlsplit(target.strip().strip("<>"))
        if not uri.scheme and not uri.netloc and uri.path:
            assert (path.parent / unquote(uri.path)).exists(), (name, target)
            links += 1
assert "- 状态：`needs_changes`" in (ROOT / DOCS[2]).read_text()
assert "needs_changes" in next(line for line in (ROOT / DOCS[1]).read_text().splitlines() if line.startswith("- T0013"))
for path in REVIEW.glob("*.py"):
    ast.parse(path.read_text(), filename=str(path))
    assert all(line == line.rstrip() for line in path.read_text().splitlines()), path
for name in ("review-r1-inputs", "review-r1-full", "review-r1-probe", "review-r1-guards"):
    path = TASK / name
    record = json.loads((path / "record.json").read_text())
    assert record["exit_code"] == 0, name
    assert record["before"]["source_sha256"] == record["after"]["source_sha256"]
    for stream in ("stdout", "stderr"):
        assert sha(str((path / (stream + ".txt")).relative_to(ROOT))) == record[stream + "_sha256"]
assert "884 passed" in (TASK / "review-r1-full/stdout.txt").read_text()
assert (TASK / "review-r1-full/stderr.txt").read_bytes() == b""
guards = json.loads((TASK / "review-r1-guards/guards.json").read_text())
assert guards["rejected_product_mutants"] == 4
assert guards["surviving_guard_mutants"] == ["root_only_import_guard"]
assert json.loads((TASK / "review-r1-probe/probe.json").read_text())["result"] == "PASS"
audit = dict(result="NEEDS_CHANGES", task_status="needs_changes", product_defect_found=False,
    product_sha256=sha("src/kmesh/logic/proof_count.py"), tests_sha256=sha("tests/test_proof_count.py"),
    full_passed=884, new_submitted_tests_passed=20, rejected_product_mutants=4,
    surviving_guard_mutants=["root_only_import_guard"],
    required_rework=["R1: A group completeness and actual variable rename", "R2: prefix isolation self-check", "R3: evidence/document corrections"],
    unchanged_submitted_files=len(before) - 3, document_links_checked=links,
    scope="product frozen; tests A/E and documentation only; no commit/push",
    review_documents={name: sha(name) for name in DOCS})
with (REVIEW / "final-audit.json").open("x") as stream:
    stream.write(json.dumps(audit, indent=2) + "\n")
print(f"PASS: review documents and {links} links; original source/history unchanged; outcome needs_changes")
