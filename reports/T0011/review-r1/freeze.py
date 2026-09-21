"""Freeze the submitted T0011 diff and verify its recorded history."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

TASK = Path("reports/T0011")
OUT = TASK / "review-r1-freeze"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    baseline = json.loads((TASK / "planning-baseline.json").read_text())
    frozen = json.loads((TASK / "planning-files.json").read_text())
    for path, digest in frozen.items():
        assert sha(path) == digest, path
    for path, digest in baseline["source_sha256"].items():
        if digest is not None:
            assert sha(path) == digest, path
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    assert head == baseline["head"]
    assert subprocess.check_output(["git", "branch", "--show-current"], text=True).strip() == "T0011-clause-key"
    allowed = set(frozen) | {"README.md", "docs/implementation_status.md", "docs/handoffs/T0011-clause-key.md"}
    allowed |= {"src/kmesh/logic/clause_key.py", "tests/test_clause_key.py"}
    changed = set()
    for args in (("diff", "HEAD", "--name-only", "-z"), ("ls-files", "--others", "--exclude-standard", "-z")):
        changed.update(p for p in subprocess.check_output(["git", *args], text=True).split("\0") if p)
    assert all(p in allowed or p.startswith("reports/T0011/") for p in changed), changed
    assert not any({"pytest-tmp", "__pycache__"}.intersection(Path(p).parts) for p in changed)
    inputs = {}
    for name in ("src/kmesh/logic/clause_key.py", "tests/test_clause_key.py", "README.md",
                 "docs/implementation_status.md", "docs/handoffs/T0011-clause-key.md"):
        target = OUT / "input-snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(name, target)
        inputs[name] = sha(name)
    history = {}
    for path in TASK.rglob("*"):
        if path.is_file() and not {"pytest-tmp", "__pycache__"}.intersection(path.parts):
            if not path.relative_to(TASK).parts[0].startswith("review-r1"):
                history[str(path)] = sha(path)
    runs = []
    for path in TASK.glob("pi-*/record.json"):
        r = json.loads(path.read_text())
        assert r["status"] == "finished", str(path)
        for stream in ("stdout", "stderr"):
            assert sha(path.parent / (stream + ".txt")) == r[stream + "_sha256"], str(path)
        for stage in ("before", "after"):
            for name, digest in baseline["source_sha256"].items():
                if digest is not None:
                    assert r[stage]["source_sha256"][name] == digest, (str(path), stage, name)
        runs.append(dict(run=path.parent.name, started=r["started_at_utc"], finished=r["finished_at_utc"],
                         elapsed_s=r["elapsed_s"], argv=r["argv"], exit_code=r["exit_code"],
                         before={p: r["before"]["source_sha256"][p] for p in inputs if p.startswith(("src/", "tests/"))},
                         after={p: r["after"]["source_sha256"][p] for p in inputs if p.startswith(("src/", "tests/"))},
                         stdout=(path.parent / "stdout.txt").read_text(), stderr=(path.parent / "stderr.txt").read_text()))
    runs.sort(key=lambda r: r["started"])
    assert runs[0]["run"] == "pi-r1-preflight" and runs[0]["exit_code"] == 0
    assert all(value is None for value in runs[0]["before"].values())
    assert all(value is None for value in runs[0]["after"].values())
    full = next(r for r in runs if r["run"] == "pi-r1-full")
    assert full["exit_code"] == 0 and "771 passed" in full["stdout"] and full["stderr"] == ""
    assert full["before"] == full["after"] == {k: v for k, v in inputs.items() if k.startswith(("src/", "tests/"))}
    (OUT / "audit.json").write_text(json.dumps(dict(head=head, input_sha256=inputs, history_sha256=history, pi_runs=runs), indent=2) + "\n")
    print(json.dumps(dict(head=head, input_sha256=inputs, immutable_history_files=len(history), run_count=len(runs),
                          runs=[{k: r[k] for k in ("run", "started", "exit_code", "elapsed_s")} for r in runs]), indent=2))


if __name__ == "__main__":
    main()
