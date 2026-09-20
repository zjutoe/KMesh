"""Freeze R2 inputs and audit the prior immutable evidence and new Pi RUNs."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

TASK = Path("reports/T0010")
OUT = TASK / "review-r2-freeze"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    prior = json.loads((TASK / "review-r1/final-audit.json").read_text())
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == prior["head"]
    for manifest in (prior["history_sha256"], prior["review_material_sha256"],
                     json.loads((TASK / "planning-files.json").read_text())):
        for p, h in manifest.items():
            assert sha(p) == h, p
    product = "src/kmesh/logic/depth.py"
    test = "tests/test_depth.py"
    assert sha(product) == prior["reviewed_files"][product]
    baseline = json.loads((TASK / "planning-baseline.json").read_text())
    for p, h in baseline["source_sha256"].items():
        if h is not None:
            assert sha(p) == h, p
    inputs = [product, test, "README.md", "docs/implementation_status.md",
              "docs/handoffs/T0010-minimum-depth.md", "reports/T0010/pi-r2-full/provenance.md"]
    for p in inputs:
        target = OUT / "input-snapshot" / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(p).read_bytes())
    before = (TASK / "review-r1-freeze/input-snapshot" / test).read_text()
    (OUT / "test_depth.py.diff").write_text("".join(difflib.unified_diff(
        before.splitlines(True), Path(test).read_text().splitlines(True), fromfile="R1", tofile="R2")))
    runs = []
    for p in sorted(TASK.glob("pi-r2*/record.json")):
        r = json.loads(p.read_text())
        assert r["status"] == "finished" and r["exit_code"] == 0, p
        assert r["before"]["source_sha256"] == r["after"]["source_sha256"], p
        for name, h in r["after"]["source_sha256"].items():
            want = prior["reviewed_files"][test] if name == test and p.parent.name == "pi-r2-preflight" else sha(name)
            assert want == h, (p, name)
        for stream in ("stdout", "stderr"):
            assert sha(p.parent / (stream + ".txt")) == r[stream + "_sha256"], p
        runs.append(dict(run=p.parent.name, **{k: r[k] for k in
                         ("argv", "started_at_utc", "finished_at_utc", "elapsed_s", "exit_code")},
                         stdout=(p.parent / "stdout.txt").read_text(), stderr=(p.parent / "stderr.txt").read_text()))
    assert len(runs) == 5
    history = {str(p): sha(p) for p in TASK.rglob("*") if p.is_file()
               and not any(s in ("__pycache__", "pytest-tmp") or s.startswith("review-r2") for s in p.parts)}
    audit = dict(head=prior["head"], input_sha256={p: sha(p) for p in inputs},
                 history_sha256=history, pi_runs=runs, prior_review_unchanged=True)
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(dict(reviewed_files={p: sha(p) for p in (product, test)}, history_files=len(history),
                         runs=[{k: r[k] for k in ("run", "exit_code", "elapsed_s")} for r in runs]), indent=2))


if __name__ == "__main__":
    main()
