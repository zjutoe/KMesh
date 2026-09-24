"""Freeze submitted T0013 inputs and verify recorded evidence without modifying it."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "reports/T0013"
OUT = TASK / "review-r1"
MUTABLE = {"README.md", "docs/implementation_status.md", "docs/handoffs/T0013-proof-count.md",
           "src/kmesh/logic/proof_count.py", "tests/test_proof_count.py"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    with (OUT / name).open("x") as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main():
    frozen = json.loads((TASK / "planning-files.json").read_text())
    for name, digest in frozen.items():
        assert sha(ROOT / name) == digest, name
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    assert head == "e576c7793a91f8508ed5c57333f81eb0188a5745"
    assert branch == "T0013-proof-count"
    paths = set(subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).decode().split("\0")) - {""}
    submitted = {}
    for name in sorted(paths):
        if name.startswith("reports/T0013/review-"):
            continue
        assert name in frozen or name in MUTABLE or name == "reports/T0013/planning-files.json" or name.startswith("reports/T0013/pi-"), name
        submitted[name] = sha(ROOT / name)
    write("frozen-inputs.json", submitted)
    for name in sorted(MUTABLE | {"reports/T0013/pi-r1/provenance.md"}):
        dest = OUT / "input-snapshot" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as stream:
            stream.write((ROOT / name).read_bytes())
    rows = []
    for path in sorted(TASK.glob("pi-*/record.json")):
        record = json.loads(path.read_text())
        assert record["status"] == "finished", path
        for channel in ("stdout", "stderr"):
            assert sha(path.parent / f"{channel}.txt") == record[f"{channel}_sha256"], path
        before, after = record["before"], record["after"]
        assert before["source_sha256"] == after["source_sha256"], path
        for name, digest in after["source_sha256"].items():
            if name in MUTABLE and path.parent.name == "pi-r1":
                assert digest is None, name
            else:
                assert sha(ROOT / name) == digest, (path, name)
        assert before["head"].strip() == after["head"].strip() == head
        rows.append({k: record[k] for k in ("argv", "exit_code", "started_at_utc", "finished_at_utc", "elapsed_s", "env_overrides")}
                    | {"run": path.parent.name,
                       "stdout": (path.parent / "stdout.txt").read_text(),
                       "stderr": (path.parent / "stderr.txt").read_text()})
    rows.sort(key=lambda row: row["started_at_utc"])
    assert len(rows) == 11
    assert rows[0]["run"] == "pi-r1"
    write("evidence-audit.json", dict(result="PASS", head=head, branch=branch,
          frozen_files=len(frozen), submitted_files=len(submitted),
          product_sha256=submitted["src/kmesh/logic/proof_count.py"],
          tests_sha256=submitted["tests/test_proof_count.py"], runs=rows))
    print(f"PASS: {len(frozen)} frozen planning/history files; {len(rows)} Pi RUNs; source snapshots and raw streams match")
    for row in rows:
        print(row["run"], row["exit_code"], row["started_at_utc"], row["elapsed_s"])
        if row["stderr"]:
            print(row["stderr"].splitlines()[-1])


if __name__ == "__main__":
    main()
