"""T0013 R2 preflight/docs checks; preserve R1 and Codex evidence."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "reports/T0013"
REVIEW = TASK / "review-r1"
TEST = "tests/test_proof_count.py"
DOCS = ("README.md", "docs/implementation_status.md", "docs/handoffs/T0013-proof-count.md")
MUTABLE = {TEST, *DOCS}


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def main():
    phase, out_name = sys.argv[1:]
    assert phase in ("preflight", "docs")
    out = (ROOT / out_name).resolve()
    assert out.parent == TASK and out.name.startswith("pi-r2") and out.is_dir()
    frozen = json.loads((REVIEW / "rework-files.json").read_text())
    for path, digest in frozen.items():
        assert sha(path) == digest, path
    paths = set(subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")) - {""}
    for path in paths:
        assert path in frozen or path in MUTABLE or path == "reports/T0013/review-r1/rework-files.json" or path.startswith("reports/T0013/pi-r2"), path
        assert not {"pytest-tmp", "__pycache__"}.intersection(Path(path).parts), path
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == "e576c7793a91f8508ed5c57333f81eb0188a5745"
    assert subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() == "T0013-proof-count"
    if phase == "preflight":
        assert sha(TEST) == "b3af8851606836b27689f1ffba6b5061542496d5b6cfba4eceb0d22a6ad55a13", "preflight precedes test edits"
        print("PASS: R2 baseline, product/history frozen, original test hash, scope")
        return
    provenance = sorted(TASK.glob("pi-r2*/provenance.md"))
    assert len(provenance) == 1, "one new R2 provenance; old R1 untouched"
    docs = [ROOT / path for path in DOCS] + provenance
    links = 0
    for path in [*docs, ROOT / TEST]:
        text = path.read_text()
        assert text.endswith("\n") and not text.endswith("\n\n")
        assert all(line == line.rstrip() for line in text.splitlines()), path
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                uri = urlsplit(target.strip().strip("<>"))
                if not uri.scheme and not uri.netloc and uri.path:
                    assert (path.parent / unquote(uri.path)).exists(), (path, target)
                    links += 1
    assert "- 状态：`awaiting_review`" in (ROOT / DOCS[2]).read_text()
    assert "awaiting_review" in next(line for line in (ROOT / DOCS[1]).read_text().splitlines() if line.startswith("- T0013"))
    example = re.search(r"```python\n(.*?)```", (ROOT / DOCS[0]).read_text().split("规范证明计数（T0013", 1)[1], re.S).group(1)
    run = subprocess.run([sys.executable, "-c", example], cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert run.returncode == 0 and run.stdout == "1\n", (run.returncode, run.stdout, run.stderr)
    rows = []
    for path in TASK.glob("pi-*/record.json"):
        if path.parent == out:
            continue
        record = json.loads(path.read_text())
        assert record["status"] == "finished", path
        for stream in ("stdout", "stderr"):
            assert sha(str((path.parent / f"{stream}.txt").relative_to(ROOT))) == record[stream + "_sha256"], path
        rows.append({k: record[k] for k in ("argv", "exit_code", "started_at_utc", "finished_at_utc", "elapsed_s")} | {"run": path.parent.name})
    rows.sort(key=lambda row: row["started_at_utc"])
    with (out / "run-index.json").open("x") as stream:
        stream.write(json.dumps(dict(runs=rows, scope="finished Pi RUNs before current docs RUN", tests_sha256=sha(TEST)), indent=2) + "\n")
    print(f"PASS: frozen product/history, scope, {len(docs)} docs/{links} links, text, README, awaiting_review")


if __name__ == "__main__":
    main()
