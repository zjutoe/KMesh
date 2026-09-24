"""Validate final review documents and record accepted source bytes."""
import ast
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "reports/T0013"
REVIEW = TASK / "review-r3"
AUDIT = REVIEW / "final-audit.json"
DOCS = ("README.md", "docs/implementation_status.md", "docs/handoffs/T0013-proof-count.md", "reports/T0013/review-r3/review.md")


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


before = json.loads((REVIEW / "frozen-inputs.json").read_text())
for name, digest in before.items():
    if name not in DOCS[:3]:
        assert sha(name) == digest, name
links = 0
deferred = []
for name in DOCS:
    path = ROOT / name
    text = path.read_text()
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert all(line == line.rstrip() for line in text.splitlines()), name
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        uri = urlsplit(target.strip().strip("<>"))
        if not uri.scheme and not uri.netloc and uri.path:
            dest = (path.parent / unquote(uri.path)).resolve()
            if dest == AUDIT:
                deferred.append(dest)  # This script creates the audit after successful checks.
            else:
                assert dest.exists(), (name, target)
            links += 1
assert "- 状态：`accepted`" in (ROOT / DOCS[2]).read_text()
assert "**状态：`accepted`（2026-09-24，Codex 第 3 轮复验" in (ROOT / DOCS[0]).read_text()
assert "**`accepted`**" in next(line for line in (ROOT / DOCS[1]).read_text().splitlines() if line.startswith("- T0013"))
for path in REVIEW.glob("*.py"):
    ast.parse(path.read_text(), filename=str(path))
    assert all(line == line.rstrip() for line in path.read_text().splitlines()), path
record = json.loads((TASK / "review-r3-checks/record.json").read_text())
assert record["exit_code"] == 0
assert record["before"]["source_sha256"] == record["after"]["source_sha256"]
for stream in ("stdout", "stderr"):
    assert sha(f"reports/T0013/review-r3-checks/{stream}.txt") == record[stream + "_sha256"]
checks = json.loads((TASK / "review-r3-checks/checks.json").read_text())
assert checks["result"] == "PASS" and checks["submitted_passed"] == 21
assert checks["prefix_self_check_effective"] is True
assert checks["runtime_blocker_observed_at"] == ["product import", "U2", "U6", "after sys.modules scan"]
result = dict(result="PASS", task_status="accepted", accepted_at_date="2026-09-24", review_round=3,
    head="e576c7793a91f8508ed5c57333f81eb0188a5745", branch="T0013-proof-count",
    accepted_files={name: sha(name) for name in ("src/kmesh/logic/proof_count.py", "tests/test_proof_count.py")},
    independent_focused_passed=21, independent_full_carried_over=884, Pi_additional_full_passed=885,
    full_rerun=False, prefix_self_check_effective=True, runtime_blocker_checkpoints=4,
    closed_findings=["R1", "R2", "R3"], open_findings=[],
    unchanged_submitted_files=len(before) - 3, document_links_checked=links,
    scope="same-world single-query complete canonical proof count; no world/motif/training acceptance",
    limitations=["model/provider are Pi self-report", "historical unknowns and process deviations retained in review-r2/review.md"],
    commit_push_performed=False, review_documents={name: sha(name) for name in DOCS})
with AUDIT.open("x") as stream:
    stream.write(json.dumps(result, indent=2) + "\n")
assert all(path.is_file() for path in deferred)
print(f"PASS: T0013 accepted; {links} document links, source/history preserved; R1-R3 closed")
