"""Verify the accepted R3 files, immutable evidence, and current review docs."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

TASK = Path("reports/T0010")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    audit = json.loads((TASK / "review-r3-freeze/audit.json").read_text())
    for path, digest in audit["history_sha256"].items():
        assert sha(path) == digest, path
    accepted = {path: audit["input_sha256"][path] for path in (
        "src/kmesh/logic/depth.py", "tests/test_depth.py")}
    for path, digest in accepted.items():
        assert sha(path) == digest, path
    for path, digest in json.loads((TASK / "planning-files.json").read_text()).items():
        assert sha(path) == digest, path
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == audit["head"]
    for name in ("review-r3-freeze", "review-r3-guards"):
        folder = TASK / name
        record = json.loads((folder / "record.json").read_text())
        assert record["status"] == "finished" and record["exit_code"] == 0, name
        assert record["before"]["source_sha256"] == record["after"]["source_sha256"], name
        for stream in ("stdout", "stderr"):
            assert sha(folder / (stream + ".txt")) == record[stream + "_sha256"], name
    guards = json.loads((TASK / "review-r3-guards/guards.json").read_text())
    assert len(guards) == 5 and all(item["guard_valid"] for item in guards)
    assert "53 passed" in (TASK / "review-r3-guards/submitted.stdout").read_text()
    old = json.loads((TASK / "review-r2/final-audit.json").read_text())
    assert old["pi_full_evidence_verified"] == 732
    docs = [Path(path) for path in (
        "README.md", "docs/implementation_status.md",
        "docs/handoffs/T0010-minimum-depth.md", "reports/T0010/review-r3/review.md")]
    links = 0
    for path in docs:
        content = path.read_text()
        assert content.endswith("\n") and all(line == line.rstrip() for line in content.splitlines()), path
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            parsed = urlsplit(link.strip().strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            assert (path.parent / unquote(parsed.path)).exists(), (path, link)
            links += 1
    assert "- 状态：`accepted`" in docs[2].read_text()
    status = next(line for line in docs[1].read_text().splitlines() if line.startswith("- T0010"))
    assert "accepted" in status and "awaiting_review" not in status
    readme = docs[0].read_text().split("单查询最短证明深度（T0010）：", 1)[1]
    assert "**状态：`accepted`" in readme and "awaiting_review" not in readme
    for path in (TASK / "review-r3").glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    allowed = {"README.md", "docs/decisions.md", "docs/handoffs/T0009-proof-enumeration.md",
               "docs/implementation_status.md", "docs/handoffs/T0010-minimum-depth.md",
               "src/kmesh/logic/depth.py", "tests/test_depth.py"}
    changed = set()
    for args in (("diff", "HEAD", "--name-only", "-z"), ("ls-files", "--others", "--exclude-standard", "-z")):
        changed.update(path for path in subprocess.check_output(["git", *args], text=True).split("\0") if path)
    assert all(path in allowed or path.startswith("reports/T0010/") for path in changed), changed
    assert not any(any(part in ("__pycache__", "pytest-tmp") for part in Path(path).parts) for path in changed)
    subprocess.run(["git", "diff", "--check"], check=True)
    summary = dict(result="PASS", task_status="accepted", closed=["R1", "R2", "R3", "R4"],
                   open_findings=[], accepted_files=accepted,
                   product_and_tests_unchanged_during_review=True,
                   prior_history_unchanged=len(audit["history_sha256"]),
                   independent_focused_passed=53, guard_cases_valid=5,
                   prior_pi_full_evidence_verified=732, full_regression_rerun=False,
                   local_links=links, document_sha256={str(path): sha(path) for path in docs},
                   limitations="Unrecorded development checks and historical model attribution remain limited; see review.md")
    (TASK / "review-r3-close/summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
