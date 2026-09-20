"""Freeze R3 and verify its narrow test edit and immutable evidence chain."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

TASK = Path("reports/T0010")
OUT = TASK / "review-r3-freeze"
ALLOWED = {"test_c4_validation_priority", "test_d2b_exception_instance_identity",
           "_swap_twin_premises", "test_depth_invariant_under_transformations"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def without_allowed_functions(text):
    lines = text.splitlines(True)
    for node in reversed(ast.parse(text).body):
        if isinstance(node, ast.FunctionDef) and node.name in ALLOWED:
            lines[node.lineno - 1:node.end_lineno] = ["FUNCTION:" + node.name + "\n"]
    return "".join(lines)


def main():
    prior = json.loads((TASK / "review-r2/final-audit.json").read_text())
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == prior["head"]
    assert subprocess.check_output(["git", "branch", "--show-current"], text=True).strip() == "T0010-minimum-depth"
    for manifest in (prior["history_sha256"], prior["review_material_sha256"],
                     json.loads((TASK / "planning-files.json").read_text())):
        for p, h in manifest.items():
            assert sha(p) == h, p
    product = "src/kmesh/logic/depth.py"
    tests = "tests/test_depth.py"
    assert sha(product) == prior["reviewed_files"][product]
    for p, h in json.loads((TASK / "planning-baseline.json").read_text())["source_sha256"].items():
        if h is not None:
            assert sha(p) == h, p
    old = (TASK / "review-r2-freeze/input-snapshot" / tests).read_text()
    new = Path(tests).read_text()
    assert without_allowed_functions(old) == without_allowed_functions(new)
    nodes_old = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(old).body if isinstance(n, ast.FunctionDef)}
    nodes_new = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(new).body if isinstance(n, ast.FunctionDef)}
    assert nodes_old.keys() == nodes_new.keys()
    changed_functions = [name for name in nodes_old if nodes_old[name] != nodes_new[name]]
    assert set(changed_functions) == ALLOWED
    inputs = [product, tests, "README.md", "docs/implementation_status.md",
              "docs/handoffs/T0010-minimum-depth.md", "reports/T0010/pi-r3-guards/provenance.md"]
    for p in inputs:
        dest = OUT / "input-snapshot" / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(p).read_bytes())
    (OUT / "test_depth.py.diff").write_text("".join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), fromfile="R2", tofile="R3")))
    runs = []
    for p in sorted(TASK.glob("pi-r3*/record.json")):
        r = json.loads(p.read_text())
        assert r["status"] == "finished" and r["exit_code"] == 0, p
        assert r["before"]["source_sha256"] == r["after"]["source_sha256"], p
        for name, h in r["after"]["source_sha256"].items():
            expected = prior["reviewed_files"][tests] if name == tests and p.parent.name == "pi-r3-preflight" else sha(name)
            assert expected == h, (p, name)
        for stream in ("stdout", "stderr"):
            assert sha(p.parent / (stream + ".txt")) == r[stream + "_sha256"], p
        runs.append(dict(run=p.parent.name, **{k: r[k] for k in
                         ("argv", "started_at_utc", "finished_at_utc", "elapsed_s", "exit_code")},
                         stdout=(p.parent / "stdout.txt").read_text(), stderr=(p.parent / "stderr.txt").read_text()))
    assert len(runs) == 4
    guards = json.loads((TASK / "pi-r3-guards/guards.json").read_text())
    assert len(guards) == 5 and all(g["guard_valid"] for g in guards)
    for g in guards:
        stdout = (TASK / "pi-r3-guards" / (g["variant"] + ".stdout")).read_text()
        if g["required_failed_test"]:
            assert g["exit_code"] == 1 and any(g["required_failed_test"] in line for line in stdout.splitlines() if line.startswith("FAILED "))
        else:
            assert g["exit_code"] == 0 and "53 passed" in stdout
    history = {str(p): sha(p) for p in TASK.rglob("*") if p.is_file()
               and not any(s in ("__pycache__", "pytest-tmp") or s.startswith("review-r3") for s in p.parts)}
    audit = dict(head=prior["head"], input_sha256={p: sha(p) for p in inputs},
                 history_sha256=history, changed_functions=changed_functions, runs=runs)
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(dict(input_sha256={p: sha(p) for p in (product, tests)}, changed_functions=changed_functions,
                         history_files=len(history), pi_runs=[{k: r[k] for k in ("run", "exit_code", "elapsed_s")} for r in runs]), indent=2))


if __name__ == "__main__":
    main()
