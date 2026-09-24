"""Check T0013 planning scope and documents without implementing its API."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "reports/T0013"
DOCS = ("docs/handoffs/T0013-proof-count.md", "docs/implementation_status.md",
        "docs/proof_identity_v1.md", "docs/decisions.md", "reports/T0013/planning-review.md")
CHANGED_TRACKED = set(DOCS[1:4])


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def main():
    baseline = json.loads((TASK / "planning-baseline.json").read_text())
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == baseline["head"]
    for name, digest in baseline["tracked_sha256"].items():
        if name not in CHANGED_TRACKED:
            assert sha(name) == digest, name
    current = {p for p in subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0") if p}
    for name in current:
        assert name in baseline["tracked_sha256"] or name == DOCS[0] or name.startswith("reports/T0013/"), name
        assert not {"pytest-tmp", "__pycache__"}.intersection(Path(name).parts), name
    for name in ("src/kmesh/logic/proof_count.py", "tests/test_proof_count.py"):
        assert not (ROOT / name).exists(), name
    for name in ("reports/T0013/pi-probe/pytest-tmp/config.yaml", "reports/T0013/__pycache__/probe.pyc"):
        subprocess.run(["git", "check-ignore", "--no-index", "-q", name], cwd=ROOT, check=True)
    for run in ("planning-preflight", "planning-examples", "planning-collection"):
        record = json.loads((TASK / run / "record.json").read_text())
        assert record["exit_code"] == 0, run
        for stream in ("stdout", "stderr"):
            assert sha(f"reports/T0013/{run}/{stream}.txt") == record[stream + "_sha256"]
        assert record["before"]["source_sha256"] == record["after"]["source_sha256"]
    assert "864 tests collected" in (TASK / "planning-collection/stdout.txt").read_text()
    fixture = json.loads((TASK / "planning-examples/examples.json").read_text())
    assert fixture["result"] == "PASS" and len(fixture["fixtures"]) == 9
    assert fixture["product_implemented"] is False
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
    for path in TASK.glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
        assert path.read_text().endswith("\n")
        assert all(line == line.rstrip() for line in path.read_text().splitlines()), path
    assert "- 状态：`ready`" in (ROOT / DOCS[0]).read_text()
    assert "`ready`" in next(line for line in (ROOT / DOCS[1]).read_text().splitlines() if line.startswith("- T0013"))
    subprocess.run(["git", "diff", "--check", "--", *sorted(CHANGED_TRACKED)], cwd=ROOT, check=True)
    summary = dict(result="PASS", task_status="ready", product_implemented=False,
                   unchanged_tracked_files=len(baseline["tracked_sha256"]) - len(CHANGED_TRACKED),
                   hand_fixtures=9, exact_budget_failures=3, unrelated_cycle_cases=2,
                   old_tests_collected=864, old_tests_executed=False,
                   document_links_checked=links, planning_documents={p: sha(p) for p in DOCS})
    out = TASK / "planning-final/summary.json"
    with out.open("x") as stream:
        stream.write(json.dumps(summary, indent=2) + "\n")
    print("PASS: planning ready; frozen baseline, scope, helpers, links and text verified")
    print("864 old tests collected only; T0013 product/test not implemented")


if __name__ == "__main__":
    main()
