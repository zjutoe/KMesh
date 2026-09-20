"""Check frozen R2 evidence and final bounded review/rework documents."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

TASK = Path("reports/T0010")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    audit = json.loads((TASK / "review-r2-freeze/audit.json").read_text())
    for p, h in audit["history_sha256"].items():
        assert sha(p) == h, p
    for p in ("src/kmesh/logic/depth.py", "tests/test_depth.py"):
        assert sha(p) == audit["input_sha256"][p], p
    for p, h in json.loads((TASK / "planning-files.json").read_text()).items():
        assert sha(p) == h, p
    for name in ("review-r2-freeze", "review-r2-guards", "review-r2-probes"):
        folder = TASK / name
        record = json.loads((folder / "record.json").read_text())
        assert record["status"] == "finished" and record["exit_code"] == 0, name
        assert record["before"]["source_sha256"] == record["after"]["source_sha256"], name
        for stream in ("stdout", "stderr"):
            assert sha(folder / (stream + ".txt")) == record[stream + "_sha256"], name
    guards = json.loads((TASK / "review-r2-guards/guards.json").read_text())
    assert all(x["guard_valid"] for x in guards)
    assert "53 passed" in (TASK / "review-r2-guards/submitted.stdout").read_text()
    full = next(x for x in audit["pi_runs"] if x["run"] == "pi-r2-full")
    assert "732 passed" in full["stdout"] and full["stderr"] == ""
    docs = [Path(p) for p in ("README.md", "docs/implementation_status.md",
                             "docs/handoffs/T0010-minimum-depth.md", "reports/T0010/review-r2/review.md")]
    links = 0
    for path in docs:
        content = path.read_text()
        assert content.endswith("\n") and all(s == s.rstrip() for s in content.splitlines()), path
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            parsed = urlsplit(link.strip().strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            assert (path.parent / unquote(parsed.path)).exists(), (path, link)
            links += 1
    assert "- 状态：`needs_changes`" in docs[2].read_text()
    assert "needs_changes" in next(s for s in docs[1].read_text().splitlines() if s.startswith("- T0010"))
    assert "**状态：`needs_changes`" in docs[0].read_text()
    for path in (TASK / "review-r2").glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    allowed = {"README.md", "docs/decisions.md", "docs/handoffs/T0009-proof-enumeration.md",
               "docs/implementation_status.md", "docs/handoffs/T0010-minimum-depth.md",
               "src/kmesh/logic/depth.py", "tests/test_depth.py"}
    changed = set()
    for args in (("diff", "HEAD", "--name-only", "-z"), ("ls-files", "--others", "--exclude-standard", "-z")):
        changed.update(p for p in subprocess.check_output(["git", *args], text=True).split("\0") if p)
    assert all(p in allowed or p.startswith("reports/T0010/") for p in changed), changed
    assert not any(any(s in ("__pycache__", "pytest-tmp") for s in Path(p).parts) for p in changed)
    subprocess.run(["git", "diff", "--check"], check=True)
    summary = dict(result="PASS", task_status="needs_changes", closed=["R3", "R4"],
                   open=["R1.1 LogicValidationError identity", "R1.2 two validation priorities", "R2.1 actual H8 swap"],
                   product_and_tests_unchanged=True, prior_history_unchanged=len(audit["history_sha256"]),
                   independent_focused_passed=53, prior_guards_valid=5,
                   pi_full_evidence_verified=732, full_regression_rerun=False,
                   local_links=links, document_sha256={str(p): sha(p) for p in docs})
    (TASK / "review-r2-close/summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
