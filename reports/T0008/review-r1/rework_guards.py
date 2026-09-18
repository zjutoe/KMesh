"""Codex-supplied R2 verification: target tests must reject two known mutants.

Run through record_check.py with its newly created RUN path as the argument.
This script never changes the product or submitted test files.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

out = Path(sys.argv[1])
assert out.is_dir() and (out / "record.json").is_file()
product_path = Path("src/kmesh/logic/derivations.py")
test_path = Path("tests/test_derivations.py")
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (product_path, test_path)}
assert before[str(product_path)] == "32634248f401865d068b13758e133037a7a9bc3dcfa409526bc7df86a9aaf29b"
source = product_path.read_text()
ground = "tests/test_derivations.py::test_two_ground_premises_match_empty_bindings"
inner = "tests/test_derivations.py::test_inner_candidate_bindings_are_independent"
failed = "tests/test_derivations.py::test_failed_inner_binding_does_not_leak"
truthiness = source.replace("if _match(first, outer_candidate, partial) is None:",
                            "if not _match(first, outer_candidate, partial):").replace(
    "if _match(second, inner_candidate, binding) is not None:",
    "if _match(second, inner_candidate, binding):")
shared = source.replace("binding = dict(partial)", "binding = partial")
assert truthiness != source and shared != source
results = []
for name, code, nodes, expected_exit in (
    ("frozen_product", source, [ground, inner, failed], 0),
    ("drop_ground_double", truthiness, [ground], 1),
    ("share_inner_binding", shared, [inner, failed], 1),
):
    args = ["-q", *nodes, "--basetemp", str(out / "pytest-tmp" / name)]
    script = (
        "import kmesh.logic.derivations as module\n"
        f"exec(compile({code!r}, '<review-guard>', 'exec'), module.__dict__)\n"
        "import pytest\n"
        f"raise SystemExit(pytest.main({args!r}))\n"
    )
    p = subprocess.run([sys.executable, "-c", script], capture_output=True,
                       text=True, timeout=30)
    for stream, value in (("stdout", p.stdout), ("stderr", p.stderr)):
        with (out / f"{name}.{stream}").open("x") as handle:
            handle.write(value)
    assert p.returncode == expected_exit, (name, p.returncode, p.stdout, p.stderr)
    assert "ERROR" not in p.stdout and "during collection" not in p.stdout, p.stdout
    if expected_exit:
        assert "AssertionError" in p.stdout and " failed" in p.stdout, p.stdout
    results.append({"case": name, "exit_code": p.returncode,
                    "summary": p.stdout.splitlines()[-1:]})
assert {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (product_path, test_path)} == before
with (out / "guards.json").open("x") as handle:
    json.dump({"result": "PASS", "cases": results, "sha256": before}, handle, indent=2)
    handle.write("\n")
print(json.dumps({"result": "PASS", "cases": results}, indent=2))
