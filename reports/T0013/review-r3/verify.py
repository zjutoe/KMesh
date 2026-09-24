"""Final bounded T0013 review: immutable evidence, focused test, runtime isolation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "reports/T0013"
REVIEW = TASK / "review-r3"
OUT = ROOT / sys.argv[1]
TEST = "tests/test_proof_count.py"
PRODUCT = "src/kmesh/logic/proof_count.py"
DOCS = {"README.md", "docs/implementation_status.md", "docs/handoffs/T0013-proof-count.md"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    with path.open("x") as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


frozen = json.loads((TASK / "review-r2/rework-files.json").read_text())
for name, digest in frozen.items():
    assert sha(ROOT / name) == digest, name
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
assert head == "e576c7793a91f8508ed5c57333f81eb0188a5745"
assert subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() == "T0013-proof-count"
paths = set(subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")) - {""}
submitted = {}
for name in sorted(paths):
    if name.startswith("reports/T0013/review-r3"):
        continue
    assert name in frozen or name in DOCS or name == TEST or name == "reports/T0013/review-r2/rework-files.json" or name.startswith("reports/T0013/pi-r3"), name
    submitted[name] = sha(ROOT / name)
write(REVIEW / "frozen-inputs.json", submitted)
for name in {TEST, PRODUCT, *DOCS, "reports/T0013/pi-r3-focused/provenance.md"}:
    target = REVIEW / "input-snapshot" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write((ROOT / name).read_bytes())
text = (ROOT / TEST).read_text()
old = (TASK / "review-r2/input-snapshot" / TEST).read_text()
assert text.split("class TestEIsolation:", 1)[0] == old.split("class TestEIsolation:", 1)[0]
records = []
for path in sorted(TASK.glob("pi-r3*/record.json")):
    record = json.loads(path.read_text())
    assert record["status"] == "finished", path
    assert record["before"]["source_sha256"] == record["after"]["source_sha256"], path
    for name, digest in record["after"]["source_sha256"].items():
        expected = (TASK / "review-r2/input-snapshot" / TEST) if name == TEST and "preflight" in path.parent.name else ROOT / name
        assert sha(expected) == digest, (path, name)
    for stream in ("stdout", "stderr"):
        assert sha(path.parent / f"{stream}.txt") == record[stream + "_sha256"], path
    records.append({k: record[k] for k in ("argv", "exit_code", "started_at_utc", "elapsed_s")} |
                   dict(run=path.parent.name, stdout=(path.parent / "stdout.txt").read_text(), stderr=(path.parent / "stderr.txt").read_text()))
records.sort(key=lambda r: r["started_at_utc"])
assert len(records) == 4 and [r["exit_code"] for r in records] == [0, 0, 1, 0]
write(REVIEW / "evidence-audit.json", dict(result="PASS", head=head, frozen_files=len(frozen),
    product_sha256=submitted[PRODUCT], tests_sha256=submitted[TEST], pre_E_unchanged=True, runs=records))
print(f"PASS: {len(frozen)} frozen files; 4 Pi R3 RUNs; all pre-E text unchanged")

condition = 'name == root or name.startswith(root + ".")'
assert text.count(condition) == 1
observed = text
assertion = '        assert any(isinstance(f, _BlockFinder) for f in sys.meta_path), "runtime import blocker removed"\n'
for marker in ('        from kmesh.logic import proof_count as pc\n',
               '        assert pc.count_canonical_proofs(u2,',
               '        assert pc.count_canonical_proofs(u6,',
               '        print("ISOLATION-OK")\n'):
    assert observed.count(marker) == 1, marker
    observed = observed.replace(marker, assertion + marker)
variants = (
    ("submitted", text, 0, None),
    ("root_only_guard", text.replace(condition, "name == root"), 1, "TestEIsolation"),
    ("runtime_guard_observation", observed, 0, "TestEIsolation"),
)
rows = []
for name, source, expected, selection in variants:
    case = OUT / "pytest-tmp" / name
    case.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT / "src", case / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    (case / "tests").mkdir()
    (case / TEST).write_text(source)
    argv = [sys.executable, "-m", "pytest", "-q", TEST, "--basetemp", str(case / "tmp")]
    if selection:
        argv += ["-k", selection]
    run = subprocess.run(argv, cwd=case, env=os.environ | {"PYTHONPATH": str(case / "src"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "CUDA_VISIBLE_DEVICES": ""}, capture_output=True, timeout=30)
    (OUT / f"{name}.stdout.txt").write_bytes(run.stdout)
    (OUT / f"{name}.stderr.txt").write_bytes(run.stderr)
    row = dict(name=name, argv=argv, cwd=str(case), exit_code=run.returncode, summary=run.stdout.decode().strip().splitlines()[-1])
    rows.append(row)
    print(name, run.returncode, row["summary"])
    assert run.returncode == expected, row
write(OUT / "checks.json", dict(result="PASS", submitted_passed=21, prefix_self_check_effective=True,
    runtime_blocker_observed_at=["product import", "U2", "U6", "after sys.modules scan"], full_rerun=False, runs=rows))
