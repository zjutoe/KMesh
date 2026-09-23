"""Freeze the accepted T0012 files and verify final documents/evidence."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "reports/T0012"
DOCS = ("README.md", "docs/implementation_status.md", "docs/handoffs/T0012-proof-key.md")


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    freeze = json.loads((TASK / "review-r5-freeze/input-audit.json").read_text())
    inputs = json.loads((TASK / "review-r5-freeze/input-manifest.json").read_text())
    for name, digest in inputs.items():
        if name not in DOCS:
            assert sha(name) == digest, f"frozen submission changed: {name}"
    current = set(git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0")) - {""}
    assert all(p in inputs or p.startswith("reports/T0012/review-r5") for p in current)
    assert not any({"pytest-tmp", "__pycache__"}.intersection(Path(p).parts) for p in current)
    assert git("rev-parse", "HEAD") == freeze["head"]
    assert git("branch", "--show-current") == "T0012-proof-key"
    assert freeze["non_b_ast_unchanged"]
    for run in ("review-r5-freeze", "review-r5-focused", "review-r5-guards", "review-r5-purity"):
        record = json.loads((TASK / run / "record.json").read_text())
        assert record["exit_code"] == 0, run
        for stream in ("stdout", "stderr"):
            assert sha(f"reports/T0012/{run}/{stream}.txt") == record[stream + "_sha256"]
        for name in ("src/kmesh/logic/proof_key.py", "tests/test_proof_key.py"):
            assert record["before"]["source_sha256"][name] == inputs[name]
            assert record["after"]["source_sha256"][name] == inputs[name]
    focused = (TASK / "review-r5-focused/stdout.txt").read_text()
    assert "69 passed" in focused and "skipped" not in focused and "xfailed" not in focused
    guards = json.loads((TASK / "review-r5-guards/guards.json").read_text())
    assert guards["all_guards_valid"] and len(guards["results"]) == 14
    assert guards["results"][0]["exit_code"] == 0
    assert all(r["exit_code"] == 1 and r["failures"] for r in guards["results"][1:])
    constants = next(r for r in guards["results"] if r["name"] == "lowercase_constants_only")
    assert any(f["name"] == "test_actual_case_differ" for f in constants["failures"])
    purity = json.loads((TASK / "review-r5-purity/purity.json").read_text())
    assert purity["result"] == "PASS"
    paths = [ROOT / p for p in DOCS] + [TASK / "review-r5/review.md"]
    links = 0
    for path in paths:
        text = path.read_text()
        assert text.endswith("\n") and all(s == s.rstrip() for s in text.splitlines()), path
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            uri = urlsplit(target.strip().strip("<>"))
            if not uri.scheme and not uri.netloc and uri.path:
                assert (path.parent / unquote(uri.path)).exists(), (path, target)
                links += 1
    assert "- 状态：`accepted`" in paths[2].read_text()
    assert "**状态：`accepted`（2026-09-23" in paths[0].read_text()
    assert "**`accepted`**" in next(s for s in paths[1].read_text().splitlines() if s.startswith("- T0012"))
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    audit_path = TASK / "review-r5/final-audit.json"
    material = {}
    for directory in TASK.glob("review-r5*"):
        if directory.name == "review-r5-close":
            continue  # The recorder finalizes this RUN after the command exits.
        for path in directory.rglob("*"):
            if path.is_file() and path != audit_path and not {"pytest-tmp", "__pycache__"}.intersection(path.parts):
                relative = str(path.relative_to(ROOT))
                material[relative] = sha(relative)
    accepted = {name: inputs[name] for name in ("src/kmesh/logic/proof_key.py", "tests/test_proof_key.py")}
    result = dict(
        result="PASS", task_status="accepted", head=freeze["head"],
        accepted_files=accepted, product_defect_found=False,
        independent_focused_tests_passed=69, full_tests_passed=None,
        carried_full_tests_passed=840, all_guards_valid=True,
        rejected_mutants=[r["name"] for r in guards["results"][1:]],
        independent_purity_supplement=purity, non_b_ast_unchanged=True,
        review_material_sha256=material,
        closure_document_sha256={p: sha(p) for p in DOCS},
        limitations=[
            "Pi pytest snapshots K3 only; Codex retained probe supplies complete K0/K3/K5 snapshots for acceptance.",
            "R5 preflight omitted; optional-preflight claim is incorrect. Current freeze cannot prove pre-edit state.",
            "R4 source sequence R4 -> R3 -> R4 remains unexplained; historical evidence gaps retained.",
            "Model/provider source is Pi self-report, not captured by the recorder.",
            "Finite same-world single-tree identity checks, not uniqueness, motif, world audit or training evidence.",
        ],
    )
    with audit_path.open("x") as output:
        output.write(json.dumps(result, indent=2) + "\n")
    print(f"PASS: frozen submission, 69 focused, 13 mutants rejected, 3-input purity supplement, {len(paths)} docs/{links} links, accepted")


if __name__ == "__main__":
    main()
