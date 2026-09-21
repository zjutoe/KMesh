"""Independent T0009 R1 probes; no product/test files are modified."""
import ast
import json
from pathlib import Path
import subprocess
import sys

from kmesh.logic.derivations import GroundDerivation
import kmesh.logic.proof_enumeration as pe
from kmesh.logic.types import Atom, Clause


def scan_counts():
    rows = []
    original_getattribute = GroundDerivation.__getattribute__
    original_enumerate = pe.enumerate_derivations
    for n in (16, 32, 64):
        stats = {"active": False, "reads": 0}

        def counted_getattribute(self, name):
            if stats["active"] and name == "conclusion":
                stats["reads"] += 1
            return original_getattribute(self, name)

        def enumerate_then_count(*args, **kwargs):
            result = original_enumerate(*args, **kwargs)
            stats["active"] = True
            return result

        clauses = (Clause((), Atom("k0", ("a", "b"))),) + tuple(
            Clause((Atom(f"k{j-1}", ("?x", "?y")),), Atom(f"k{j}", ("?x", "?y")))
            for j in range(1, n + 1)
        )
        try:
            GroundDerivation.__getattribute__ = counted_getattribute
            pe.enumerate_derivations = enumerate_then_count
            try:
                pe.enumerate_proofs(clauses, Atom(f"k{n}", ("a", "b")),
                                    max_fact_checks=n, max_derivations=n + 1, max_proof_steps=1)
            except pe.ProofEnumerationLimitError as exc:
                assert str(exc) == "proofs.max_proof_steps exhausted before enumeration completed"
            else:
                raise AssertionError("expected proof-budget exhaustion")
        finally:
            stats["active"] = False
            GroundDerivation.__getattribute__ = original_getattribute
            pe.enumerate_derivations = original_enumerate
        rows.append({"rules": n, "records": n + 1, "conclusion_reads_after_T0008": stats["reads"],
                     "regression_upper_bound": 8 * (n + 1)})
    return rows


def main():
    out = Path(sys.argv[1])
    source = Path("src/kmesh/logic/proof_enumeration.py").read_text()
    generator_mutant = source.replace(
        "    if not isinstance(clauses, tuple):\n",
        "    if type(clauses).__name__ == 'generator':\n        next(clauses, None)\n"
        "    if not isinstance(clauses, tuple):\n", 1)
    validate_s = '    steps_budget = _require_budget("max_proof_steps", max_proof_steps)\n'
    after_t8 = "        clauses, max_fact_checks=fact_checks, max_derivations=derivations\n    )\n"
    assert source.count(validate_s) == source.count(after_t8) == 1
    late_s_mutant = source.replace(validate_s, "").replace(after_t8, after_t8 + validate_s)
    variants = (
        ("generator_consumed_once", generator_mutant, ["test_clauses_container_diagnostics"]),
        ("proof_budget_validated_after_T0008", late_s_mutant,
         ["test_validation_priority_chain", "test_t0008_not_called_on_invalid_input", "test_budget_diagnostics"]),
    )
    results = []
    for name, mutated, selected in variants:
        assert mutated != source
        code = (
            "import pytest\nimport kmesh.logic.proof_enumeration as pe\n"
            f"exec(compile({mutated!r},'<review-memory-mutant>','exec'),pe.__dict__)\n"
            f"raise SystemExit(pytest.main({['-q',*[f'tests/test_proof_enumeration.py::{test}' for test in selected],'--basetemp',str(out/'pytest-tmp'/name)]!r}))\n"
        )
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
        (out / f"{name}.stdout").write_text(p.stdout)
        (out / f"{name}.stderr").write_text(p.stderr)
        assert p.returncode == 0, (name, p.stdout, p.stderr)
        results.append({"mutation": name, "exit_code": p.returncode,
                        "finding": "submitted targeted tests did not reject known-invalid behavior",
                        "summary": p.stdout.splitlines()[-1]})
    tree = ast.parse(source)
    recursive = [f.name for f in tree.body if isinstance(f, ast.FunctionDef)
                 and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == f.name
                         for n in ast.walk(f))]
    findings = {"scan_counts": scan_counts(), "recursive_helpers": recursive,
                "test_guard_gaps": results}
    (out / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
