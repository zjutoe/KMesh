"""Freeze submitted inputs and check original Pi evidence without rewriting it."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path.cwd()
TASK = Path("reports/T0010")
OUT = TASK / "review-r1-freeze"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    baseline = json.loads((TASK / "planning-baseline.json").read_text())
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == baseline["head"]
    for name, digest in baseline["source_sha256"].items():
        if digest is not None:
            assert sha(name) == digest, name
    for name, digest in json.loads((TASK / "planning-files.json").read_text()).items():
        assert sha(name) == digest, name
    inputs = ["src/kmesh/logic/depth.py", "tests/test_depth.py", "README.md",
              "docs/implementation_status.md", "docs/handoffs/T0010-minimum-depth.md",
              "reports/T0010/pi-r1-full/provenance.md"]
    for name in inputs:
        target = OUT / "input-snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(name).read_bytes())
    runs = []
    for path in sorted(TASK.glob("pi-*/record.json")):
        r = json.loads(path.read_text())
        assert r["status"] == "finished", path
        assert r["before"]["source_sha256"] == r["after"]["source_sha256"], path
        for name, digest in r["after"]["source_sha256"].items():
            if name in inputs[:2] and path.parent.name == "pi-r1-preflight":
                assert digest is None, (path, name)
            else:
                assert sha(name) == digest, (path, name)
        for stream in ("stdout", "stderr"):
            assert sha(path.parent / (stream + ".txt")) == r[stream + "_sha256"], path
        assert r["exit_code"] == (1 if path.parent.name == "pi-r1-docs" else 0)
        runs.append(dict(run=path.parent.name,
                         **{k: r[k] for k in ("argv", "started_at_utc", "finished_at_utc", "elapsed_s", "exit_code")},
                         stdout=(path.parent / "stdout.txt").read_text(),
                         stderr=(path.parent / "stderr.txt").read_text()))
    history = {str(p): sha(p) for p in TASK.rglob("*") if p.is_file()
               and not any(s in ("__pycache__", "pytest-tmp") or s.startswith("review-") for s in p.parts)}
    audit = dict(head=baseline["head"], input_sha256={p: sha(p) for p in inputs},
                 history_sha256=history, runs=runs)
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(dict(input_sha256=audit["input_sha256"], history_files=len(history),
                         pi_runs=[{k: r[k] for k in ("run", "exit_code", "elapsed_s")} for r in runs]), indent=2))


if __name__ == "__main__":
    main()
