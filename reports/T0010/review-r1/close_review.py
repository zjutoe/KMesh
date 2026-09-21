"""Check review records, frozen inputs and final review documentation."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path.cwd()
TASK = Path("reports/T0010")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    frozen = json.loads((TASK / "review-r1-freeze/audit.json").read_text())
    for name, digest in frozen["history_sha256"].items():
        assert sha(name) == digest, name
    for name in ("src/kmesh/logic/depth.py", "tests/test_depth.py"):
        assert sha(name) == frozen["input_sha256"][name], name
    for name, digest in json.loads((TASK / "planning-files.json").read_text()).items():
        assert sha(name) == digest, name
    for run in ("review-r1-freeze", "review-r1-full", "review-r1-mutations", "review-r1-probes"):
        path = TASK / run
        r = json.loads((path / "record.json").read_text())
        assert r["status"] == "finished" and r["exit_code"] == 0, run
        assert r["before"]["source_sha256"] == r["after"]["source_sha256"], run
        for stream in ("stdout", "stderr"):
            assert sha(path / (stream + ".txt")) == r[stream + "_sha256"], run
    assert "719 passed" in (TASK / "review-r1-full/stdout.txt").read_text()
    assert not (TASK / "review-r1-full/stderr.txt").read_text()
    docs = [Path(p) for p in ("README.md", "docs/implementation_status.md",
                             "docs/handoffs/T0010-minimum-depth.md", "reports/T0010/review-r1/review.md")]
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
    for path in (TASK / "review-r1").glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    allowed = {"README.md", "docs/decisions.md", "docs/handoffs/T0009-proof-enumeration.md",
               "docs/handoffs/T0010-minimum-depth.md", "docs/implementation_status.md",
               "src/kmesh/logic/depth.py", "tests/test_depth.py"}
    changed = set()
    for args in (("diff", "HEAD", "--name-only", "-z"), ("ls-files", "--others", "--exclude-standard", "-z")):
        changed.update(p for p in subprocess.check_output(["git", *args], text=True).split("\0") if p)
    assert all(p in allowed or p.startswith("reports/T0010/") for p in changed), changed
    assert not any("pytest-tmp" in Path(p).parts or "__pycache__" in Path(p).parts for p in changed)
    subprocess.run(["git", "diff", "--check"], check=True)
    summary = dict(result="PASS", task_status="needs_changes", frozen_product_tests_unchanged=True,
                   historical_files_unchanged=len(frozen["history_sha256"]), local_links=links,
                   current_document_sha256={str(p): sha(p) for p in docs})
    (TASK / "review-r1-close/summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
