"""Rework gate: submitted guards must reject two in-memory wrong versions.

Never writes product/tests. Run through the recorder with a fresh RUN output.
"""
import json
from pathlib import Path
import subprocess
import sys


def main():
    out = Path(sys.argv[1])
    source = Path("src/kmesh/logic/proof_enumeration.py").read_text()
    container = "    if not isinstance(clauses, tuple):\n"
    validate_s = '    steps_budget = _require_budget("max_proof_steps", max_proof_steps)\n'
    after_t8 = "        clauses, max_fact_checks=fact_checks, max_derivations=derivations\n    )\n"
    assert source.count(container) == source.count(validate_s) == source.count(after_t8) == 1
    consumed = source.replace(container,
        "    if type(clauses).__name__ == 'generator':\n        next(clauses, None)\n" + container)
    late = source.replace(validate_s, "").replace(after_t8, after_t8 + validate_s)
    selected = ["test_clauses_container_diagnostics", "test_validation_priority_chain",
                "test_t0008_not_called_on_invalid_input"]
    results = []
    for name, mutated, expected in (("submitted", source, 0),
                                   ("generator_consumed_once", consumed, 1),
                                   ("proof_budget_after_T0008", late, 1)):
        argv = ["-q", *[f"tests/test_proof_enumeration.py::{test}" for test in selected],
                "--basetemp", str(out / "pytest-tmp" / name)]
        code = ("import pytest\nimport kmesh.logic.proof_enumeration as pe\n"
                f"exec(compile({mutated!r},'<review-memory-guard>','exec'),pe.__dict__)\n"
                f"raise SystemExit(pytest.main({argv!r}))\n")
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
        (out / f"{name}.stdout").write_text(p.stdout)
        (out / f"{name}.stderr").write_text(p.stderr)
        assert p.returncode == expected, (name, expected, p.returncode, p.stdout, p.stderr)
        if expected:
            target = selected[0] if name == "generator_consumed_once" else selected[1]
            assert f"FAILED tests/test_proof_enumeration.py::{target}" in p.stdout
        results.append({"case": name, "exit_code": p.returncode,
                        "summary": p.stdout.splitlines()[-1]})
    result = {"result": "PASS", "cases": results}
    (out / "guards.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
