"""Close the bounded R2 review while preserving all submitted evidence."""
import ast
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "reports/T0013"
REVIEW = TASK / "review-r2"
DOCS = ("README.md", "docs/implementation_status.md", "docs/handoffs/T0013-proof-count.md", "reports/T0013/review-r2/review.md")


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
record = json.loads((TASK / "review-r2-checks/record.json").read_text())
assert record["exit_code"] == 0
assert record["before"]["source_sha256"] == record["after"]["source_sha256"]
for stream in ("stdout", "stderr"):
    assert sha(f"reports/T0013/review-r2-checks/{stream}.txt") == record[stream + "_sha256"]
checks = json.loads((TASK / "review-r2-checks/checks.json").read_text())
assert checks["submitted_passed"] == 21 and checks["prefix_self_check_effective"] is True
assert checks["runtime_blocker_present"] is False
result = dict(result="NEEDS_CHANGES", task_status="needs_changes", product_defect_found=False,
    product_sha256=sha("src/kmesh/logic/proof_count.py"), tests_sha256=sha("tests/test_proof_count.py"),
    independent_focused_passed=21, independent_full_carried_over=884, Pi_additional_full_passed=885,
    closed=["R1: A group", "R2: root/prefix self-check", "R3: Codex appended corrections with permanent unknowns"],
    open=["R2: keep import finder installed during real product imports and U2/U6 calls"],
    unchanged_submitted_files=len(before) - 3, document_links_checked=links,
    scope="E group only; product/A-D frozen; no commit/push",
    review_documents={name: sha(name) for name in DOCS})
with (REVIEW / "final-audit.json").open("x") as stream:
    stream.write(json.dumps(result, indent=2) + "\n")
print(f"PASS: source/history preserved, {links} document links; needs_changes limited to runtime finder removal")
